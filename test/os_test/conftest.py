"""Shared infrastructure for the OS-level install/update tests.

These tests build a throwaway OS (a Debian container for Tier 1, an isolated
QEMU ARM64 VM for Tier 2), run the real installer inside it, and then verify
the resulting OS state with
``probe.py``.

They are slow and need root/docker, so the whole directory is skipped unless
``WAQD_OS_TEST=1`` is set - the same gating pattern as
``test/waqd_station/hardware/conftest.py`` uses with ``WAQD_HW_CONNECTED``.

Run from the repo root with the venv active:

    WAQD_OS_TEST=1 pdm run pytest test/os_test -q --timeout=1800
"""

import json
import os
import shlex
import selectors
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).parent
REPO_ROOT = TEST_DIR.parent.parent
PROBE_PATH = TEST_DIR / "probe.py"
INSTALLER_SCRIPT = REPO_ROOT / "script" / "installer" / "start_installer.sh"
INSTALLER_CONTAINER_SCRIPT = "/waqd/script/installer/start_installer.sh"

# User the installer targets inside the system under test.
TARGET_USER = "pi"

# Container runtime: podman or docker. Set WAQD_CONTAINER_RUNTIME to force one,
# otherwise auto-detect (podman first, since it is rootless-friendly).
CONTAINER_RUNTIME = os.getenv("WAQD_CONTAINER_RUNTIME", "").strip().lower()
OS_TEST_LOG = Path(os.getenv("WAQD_OS_TEST_LOG", "/tmp/waqd-os-test.log"))


def _log(message):
    """Append a timestamped diagnostic message to the OS-test log."""
    OS_TEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with OS_TEST_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")
        log_file.flush()
        os.fsync(log_file.fileno())


# Start a fresh log for each pytest process. Subprocess output is appended by
# _run, so a failed run can be inspected without immediately rerunning it.
OS_TEST_LOG.parent.mkdir(parents=True, exist_ok=True)
OS_TEST_LOG.write_text(
    f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] OS test log started\n",
    encoding="utf-8",
)


def container_runtime() -> str:
    """Return the container CLI to use: 'podman' or 'docker'."""
    if CONTAINER_RUNTIME in ("podman", "docker"):
        return CONTAINER_RUNTIME
    if CONTAINER_RUNTIME:
        raise RuntimeError(
            f"WAQD_CONTAINER_RUNTIME must be 'podman' or 'docker', got {CONTAINER_RUNTIME!r}"
        )
    for candidate in ("podman", "docker"):
        if shutil.which(candidate):
            return candidate
    return "docker"  # will fail later with a clear skip message


def pytest_collection_modifyitems(config, items):
    """Skip everything here unless WAQD_OS_TEST is set."""
    if os.getenv("WAQD_OS_TEST", "").strip():
        return
    skip = pytest.mark.skip(reason="set WAQD_OS_TEST=1 to run OS-level install tests")
    for item in items:
        if item.get_closest_marker("os_test"):
            item.add_marker(skip)


def _run(cmd, check=False, timeout=900, **kwargs):
    """Run a command, streaming stdout/stderr to the persistent test log."""
    command = " ".join(str(part) for part in cmd)
    _log(f"RUN ({timeout}s): {command}")
    kwargs.pop("capture_output", None)
    kwargs.pop("text", None)
    kwargs.pop("timeout", None)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        **kwargs,  # noqa: S603
    )
    output = {"stdout": [], "stderr": []}
    selector = selectors.DefaultSelector()
    assert proc.stdout is not None
    assert proc.stderr is not None
    selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
    selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
    deadline = time.monotonic() + timeout
    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            proc.kill()
            selector.close()
            raise subprocess.TimeoutExpired(cmd, timeout)
        for key, _ in selector.select(remaining):
            stream_file = key.fileobj
            line = stream_file.readline()  # type: ignore[union-attr]
            if line == "":
                selector.unregister(key.fileobj)
                stream_file.close()  # type: ignore[union-attr]
                continue
            stream = key.data
            output[stream].append(line)
            _log(f"{stream.upper()} {command}: {line.rstrip()}")
    returncode = proc.wait()
    stdout = "".join(output["stdout"])
    stderr = "".join(output["stderr"])
    _log(f"EXIT {returncode}: {command}")
    if check and returncode != 0:
        raise RuntimeError(
            f"Command failed ({returncode}): {' '.join(str(c) for c in cmd)}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        )
    return returncode, stdout, stderr


class SystemUnderTest:
    """Abstraction over 'a running OS we can execute commands in'.

    Subclasses implement ``exec`` for docker containers and QEMU machines so
    the tests themselves stay identical across tiers.
    """

    def exec(self, cmd, user=None, check=False, timeout=900):
        raise NotImplementedError

    def copy_in(self, src: Path, dest: str):
        raise NotImplementedError

    def probe(self, checks=("all",), version="", user=TARGET_USER, timeout=300):
        """Run probe.py inside the system and return (ok, passed, failed, skipped)."""
        _log(f"PROBE checks={checks} version={version or '<none>'} user={user}")
        self.copy_in(PROBE_PATH, "/tmp/waqd_probe.py")
        cmd = ["python3", "/tmp/waqd_probe.py", *checks, "--user", user, "--json"]
        if version:
            cmd += ["--version", version]
        rc, out, err = self.exec(cmd, timeout=timeout)
        if rc not in (0, 1):  # 1 == probe ran but some checks failed
            raise RuntimeError(f"probe.py crashed:\n{out}\n{err}")
        try:
            summary = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError) as e:
            raise RuntimeError(f"could not parse probe output:\n{out}\n{err}") from e
        return (not summary["failed"]), summary["passed"], summary["failed"], summary["skipped"]

    def install(self, extra_env=None, timeout=3600):
        """Run the real installer entry point, non-interactively."""
        _log(
            "INSTALL start: WAQD_SKIP_REBOOT=1 dbus-run-session "
            "systemd --user start_installer.sh --no-gui"
        )
        env = "WAQD_SKIP_REBOOT=1 " + (extra_env or "")
        # A real LXDE login gives the installer both a session bus and a
        # per-user systemd manager. `podman exec -u pi` provides neither, so
        # create the same small session explicitly. The manager is kept alive
        # for the duration of the install and then cleaned up by the trap.
        self.exec(
            [
                "install",
                "-d",
                "-m",
                "700",
                "-o",
                "pi",
                "-g",
                "pi",
                "/run/user/1000",
            ],
            check=True,
        )
        session_script = (
            "systemd --user & manager_pid=$!; "
            "trap 'kill $manager_pid 2>/dev/null || true' EXIT; "
            "for attempt in $(seq 1 20); do "
            "systemctl --user is-system-running >/dev/null 2>&1 && break; "
            "sleep 0.2; "
            "done; "
            f"{env} bash {INSTALLER_CONTAINER_SCRIPT} --no-gui"
        )
        return self.exec(
            [
                "env",
                "XDG_RUNTIME_DIR=/run/user/1000",
                "dbus-run-session",
                "--",
                "bash",
                "-c",
                session_script,
            ],
            user=TARGET_USER,
            timeout=timeout,
        )


class ContainerSUT(SystemUnderTest):
    """A long-running container (podman or docker) used as the system under test."""

    def __init__(self, image, name, runtime=None):
        self.image = image
        self.name = name
        self.runtime = runtime or container_runtime()

    @classmethod
    def start(cls, image, name, extra_run_args=None, runtime=None):
        rt = runtime or container_runtime()
        _log(f"CONTAINER start runtime={rt} image={image} name={name}")
        _run([rt, "rm", "-f", name])  # clean up a previous run
        cmd = [
            rt,
            "run",
            "-d",
            "--name",
            name,
            "--privileged",
            "--user",
            "root",
            "--systemd=always" if rt == "podman" else "--init",
            "--tmpfs",
            "/run",
            "--tmpfs",
            "/run/lock",
            "-v",
            "/sys/fs/cgroup:/sys/fs/cgroup:rw",
            *(extra_run_args or []),
            image,
        ]
        # Use systemd as PID 1: the installer configures system services and
        # user services, so a sleep process is not a valid system under test.
        cmd += ["/sbin/init"]
        _run(cmd, check=True)
        sut = cls(image, name, runtime=rt)
        sut._wait_ready()
        return sut

    def _wait_ready(self, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            rc, _, _ = _run([self.runtime, "exec", self.name, "true"])
            if rc == 0:
                return
            time.sleep(1)
        raise RuntimeError(f"container {self.name} never became ready")

    def exec(self, cmd, user=None, check=False, timeout=900):
        rt_cmd = [self.runtime, "exec"]
        if user:
            rt_cmd += ["-u", user]
        rt_cmd += [self.name, *cmd]
        return _run(rt_cmd, check=check, timeout=timeout)

    def copy_in(self, src: Path, dest: str):
        _run([self.runtime, "cp", str(src), f"{self.name}:{dest}"], check=True)

    def stop(self):
        _log(f"CONTAINER stop runtime={self.runtime} name={self.name}")
        _run([self.runtime, "rm", "-f", self.name])


class QemuSUT(SystemUnderTest):
    """An isolated Raspberry Pi OS VM controlled only through SSH."""

    def __init__(self, workdir: Path, port: int, key: Path, process):
        self.workdir = workdir
        self.port = port
        self.key = key
        self.process = process

    def _ssh(self, cmd, user=None):
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=10",
            "-i",
            str(self.key),
            "-p",
            str(self.port),
            f"{user or TARGET_USER}@127.0.0.1",
            "--",
            " ".join(shlex.quote(str(part)) for part in cmd),
        ]

    def exec(self, cmd, user=None, check=False, timeout=900):
        if user is None:
            # SSH is established as pi. Root operations use the prepared
            # passwordless sudo rule, matching the old container/nspawn
            # adapters without requiring host privileges.
            cmd = ["sudo", "-n", *cmd]
            user = TARGET_USER
        return _run(self._ssh(cmd, user), check=check, timeout=timeout)

    def copy_in(self, src: Path, dest: str):
        _run(
            [
                "scp",
                "-q",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-i",
                str(self.key),
                "-P",
                str(self.port),
                str(src),
                f"{TARGET_USER}@127.0.0.1:{dest}",
            ],
            check=True,
            timeout=120,
        )

    def reboot(self, timeout=180):
        self.exec(["sudo", "-n", "reboot"], user=TARGET_USER, timeout=30)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rc, _, _ = self.exec(["true"], timeout=20)
            if rc == 0:
                return
            time.sleep(2)
        raise RuntimeError("Raspberry Pi OS QEMU guest did not return after reboot")


@pytest.fixture(scope="module")
def rpios_machine():
    """Start an isolated ARM64 QEMU VM and destroy it after the module."""
    for tool in ("qemu-system-aarch64", "qemu-img", "ssh", "scp"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} is required for the QEMU RPi OS test")
    cache_dir = Path(
        os.getenv("WAQD_RPIOS_CACHE_DIR", str(Path.home() / ".cache" / "waqd-os-test"))
    )
    image_override = os.getenv("WAQD_RPIOS_IMAGE", "").strip()
    fetch_script = REPO_ROOT / "script" / "os_test" / "fetch_rpios_image.sh"
    qemu_script = REPO_ROOT / "script" / "os_test" / "run_qemu.sh"
    append = os.getenv(
        "WAQD_QEMU_APPEND",
        "root=/dev/vda2 rw rootwait console=ttyAMA0,115200 systemd.unit=multi-user.target",
    )

    if image_override:
        image = Path(image_override).expanduser()
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)
        fetch = subprocess.run(
            [str(fetch_script), str(cache_dir)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=1800,
        )
        if fetch.returncode != 0:
            pytest.fail(
                f"could not fetch Raspberry Pi OS image:\n{fetch.stdout}\n{fetch.stderr}"
            )
        image = Path(fetch.stdout.strip().splitlines()[-1])
    if not image.is_file():
        pytest.fail(f"Raspberry Pi OS image does not exist: {image}")
    workdir = Path(tempfile.mkdtemp(prefix="waqd-qemu-"))
    port = int(os.getenv("WAQD_QEMU_SSH_PORT", "0"))
    if port == 0:
        import socket

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
    key_value = os.getenv("WAQD_QEMU_SSH_KEY", "").strip()
    if not key_value:
        pytest.skip("WAQD_QEMU_SSH_KEY must point to the private key installed in the guest")
    key = Path(key_value).expanduser()
    if not key.is_file():
        pytest.skip(f"QEMU SSH private key does not exist: {key}")
    env = os.environ.copy()
    env.update(
        WAQD_QEMU_SSH_PORT=str(port),
        WAQD_QEMU_WORKDIR=str(workdir),
        WAQD_QEMU_APPEND=append,
        WAQD_QEMU_SSH_KEY=str(key),
    )
    process = subprocess.Popen(
        [str(qemu_script), str(image), str(workdir)],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + int(os.getenv("WAQD_QEMU_START_TIMEOUT", "180"))
        sut = QemuSUT(workdir, port, key, process)
        while time.monotonic() < deadline:
            rc, _, _ = sut.exec(["true"], timeout=10)
            if rc == 0:
                yield sut
                return
            if process.poll() is not None:
                pytest.fail(f"QEMU exited with {process.returncode}; see {workdir}")
            time.sleep(1)
        pytest.fail(f"QEMU did not start within {deadline}; see {workdir}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def container_cli():
    """The container runtime in use ('podman' or 'docker')."""
    rt = container_runtime()
    if not shutil.which(rt):
        pytest.skip(f"{rt} not available (set WAQD_CONTAINER_RUNTIME to override)")
    return rt


@pytest.fixture(scope="session")
def require_docker(container_cli):
    """Skip unless the container runtime is actually usable."""
    rc, _, err = _run([container_cli, "info"])
    if rc != 0:
        pytest.skip(f"{container_cli} is not usable: {err.strip()}")


@pytest.fixture(scope="session")
def require_root_tools():
    """Require the unprivileged tools used by the QEMU tier."""
    for tool in ("qemu-system-aarch64", "qemu-img", "ssh", "scp"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} not available")


@pytest.fixture
def assert_probe():
    """Return a helper that runs the probe and turns failures into a good message."""

    def _assert(sut, checks=("all",), version="", user=TARGET_USER, timeout=300):
        ok, passed, failed, skipped = sut.probe(
            checks=checks, version=version, user=user, timeout=timeout
        )
        assert ok, f"probe checks FAILED: {failed}\npassed: {passed}\nskipped: {skipped}"
        return passed, skipped

    return _assert
