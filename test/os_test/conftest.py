"""Shared infrastructure for the OS-level install/update tests.

These tests build a throwaway OS (a Debian container for Tier 1, a real
Raspberry Pi OS image booted with systemd-nspawn for Tier 2), run the real
installer inside it, and then verify the resulting OS state with
``probe.py``.

They are slow and need root/docker, so the whole directory is skipped unless
``WAQD_OS_TEST=1`` is set - the same gating pattern as
``test/waqd_station/hardware/conftest.py`` uses with ``WAQD_HW_CONNECTED``.

Run from the repo root with the venv active:

    WAQD_OS_TEST=1 pdm run pytest test/os_test -q --timeout=1800
"""

import json
import os
import signal
import selectors
import shutil
import subprocess
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
            line = key.fileobj.readline()
            if line == "":
                selector.unregister(key.fileobj)
                key.fileobj.close()
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


def _privileged_command(cmd):
    """Prefix a host command with sudo when pytest is not already root."""
    return cmd if os.geteuid() == 0 else ["sudo", "-n", *cmd]


def _cleanup_stale_nspawn_mounts():
    """Unmount leftovers from interrupted nspawn runs before starting again."""
    for mountpoint in sorted(Path("/tmp").glob("waqd-nspawn.*")):
        if not mountpoint.is_dir():
            continue
        # A surviving nspawn process keeps the directory busy even after the
        # machine registration disappears. Kill only nspawn processes whose
        # --directory points at this exact temporary root.
        ps = subprocess.run(
            ["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=False
        )
        for line in ps.stdout.splitlines():
            fields = line.strip().split(None, 1)
            if len(fields) == 2 and "systemd-nspawn" in fields[1]:
                if f"--directory {mountpoint}" in fields[1]:
                    _run(_privileged_command(["kill", "-TERM", fields[0]]), timeout=30)
        _run(_privileged_command(["umount", "-R", "-l", str(mountpoint)]), timeout=120)
        if _run(["mountpoint", "-q", str(mountpoint)])[0] == 0:
            raise RuntimeError(
                f"could not unmount stale nspawn rootfs {mountpoint}; "
                "run with sudo or close processes using that directory"
            )
        try:
            mountpoint.rmdir()
        except OSError:
            pass


class SystemUnderTest:
    """Abstraction over 'a running OS we can execute commands in'.

    Subclasses implement ``exec`` for docker containers and nspawn machines so
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


class NspawnSUT(SystemUnderTest):
    """A real Raspberry Pi OS image booted with systemd-nspawn.

    ``systemd-nspawn --boot`` gives a genuine PID 1 inside the machine, so a
    ``reboot`` issued by the installer restarts the container's init rather
    than the host. This is the only tier that exercises the reboot for real.
    """

    def __init__(self, name, root: Path):
        self.name = name
        self.root = root

    def exec(self, cmd, user=None, check=False, timeout=900):
        nspawn = ["systemd-nspawn", "-M", self.name, "-D", str(self.root), "--pipe", "-q"]
        if user:
            nspawn += ["-u", user]
        return _run(_privileged_command([*nspawn, *cmd]), check=check, timeout=timeout)

    def copy_in(self, src: Path, dest: str):
        target = self.root / dest.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, target)

    def reboot(self, timeout=180):
        """Reboot the machine and wait for it to come back."""
        _run(_privileged_command(["machinectl", "reboot", self.name]), timeout=60)
        deadline = time.time() + timeout
        while time.time() < deadline:
            rc, _, _ = self.exec(["true"], timeout=30)
            if rc == 0:
                return
            time.sleep(2)
        raise RuntimeError(f"machine {self.name} did not come back after reboot")


@pytest.fixture(scope="module")
def rpios_machine(request):
    """Automatically fetch, boot, and clean up the RPi OS test machine.

    The fixture owns the complete lifecycle. A developer only needs to run
    pytest with ``WAQD_OS_TEST=1``; the official image is fetched from the
    local cache and nspawn is started and stopped automatically.
    """
    if os.getenv("WAQD_OS_TEST_MANUAL_NSPAWN", "0") == "1":
        yield None
        return

    if os.geteuid() != 0 and not shutil.which("sudo"):
        pytest.skip("RPi OS tests need root or sudo for nspawn")
    if os.geteuid() != 0 and _run(["sudo", "-n", "true"])[0] != 0:
        pytest.skip(
            "RPi OS tests need an authenticated, noninteractive sudo session; "
            "run `sudo -v` once before pytest so it can clean up nspawn mounts "
            "on success and failure"
        )
    for tool in ("systemd-nspawn", "losetup", "machinectl"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} is required for RPi OS tests")

    machine = os.getenv("WAQD_OS_TEST_MACHINE", "waqd-os-test")
    if _run(["machinectl", "show", machine])[0] == 0:
        _run(_privileged_command(["machinectl", "poweroff", machine]), timeout=120)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and _run(["machinectl", "show", machine])[0] == 0:
            time.sleep(1)
    _cleanup_stale_nspawn_mounts()
    # Recent systemd-nspawn versions use nsresourced for namespace resource
    # setup. It is socket-activated on the host, but starting the socket here
    # makes the fixture independent of the host's boot-time service state.
    _run(
        _privileged_command(["systemctl", "start", "systemd-nsresourced.socket"]),
        timeout=60,
    )
    cache_dir = Path(
        os.getenv("WAQD_RPIOS_CACHE_DIR", str(Path.home() / ".cache" / "waqd-os-test"))
    )
    image_override = os.getenv("WAQD_RPIOS_IMAGE", "").strip()
    fetch_script = REPO_ROOT / "script" / "os_test" / "fetch_rpios_image.sh"
    nspawn_script = REPO_ROOT / "script" / "os_test" / "run_nspawn.sh"
    log_path = Path(os.getenv("WAQD_NSPAWN_LOG", f"/tmp/{machine}-nspawn.log"))

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
    arm_reason = _rpios_can_execute_arm64()
    if arm_reason:
        pytest.skip(arm_reason)

    if _run(["machinectl", "show", machine])[0] == 0:
        root = _find_nspawn_root(machine)
        if root:
            yield NspawnSUT(machine, root)
            return
        pytest.fail(f"machine {machine!r} is running but its root directory is unknown")

    log_file = log_path.open("w", encoding="utf-8")
    command = [str(nspawn_script), str(image), machine]
    if os.geteuid() == 0:
        launch = command
    else:
        # The earlier sudo probe may have been performed before image
        # resolution. Revalidate immediately before spawning the long-lived
        # privileged process; otherwise sudo can fail inside Popen and only
        # leave the unhelpful message in the nspawn log.
        sudo_check = subprocess.run(
            ["sudo", "-n", "-v"], capture_output=True, text=True, check=False
        )
        if sudo_check.returncode != 0:
            log_file.close()
            pytest.skip(
                "sudo credentials are not currently cached for noninteractive "
                "use; run `sudo -v` immediately before pytest"
            )
        launch = ["sudo", "-n", *command]
    _log(f"NSPAWN launch: {' '.join(launch)} log={log_path}")
    process = subprocess.Popen(
        launch,
        cwd=REPO_ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + int(os.getenv("WAQD_NSPAWN_START_TIMEOUT", "180"))
        while time.monotonic() < deadline:
            if _run(["machinectl", "show", machine])[0] == 0:
                root = _find_nspawn_root(machine)
                if root:
                    yield NspawnSUT(machine, root)
                    return
            if process.poll() is not None:
                log_file.flush()
                pytest.fail(
                    f"nspawn exited with {process.returncode}; see {log_path}\n"
                    f"{log_path.read_text(encoding='utf-8', errors='replace')}"
                )
            time.sleep(1)
        pytest.fail(f"nspawn did not start within {deadline}; see {log_path}")
    finally:
        log_file.close()
        if _run(["machinectl", "show", machine])[0] == 0:
            _run(_privileged_command(["machinectl", "poweroff", machine]), timeout=120)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if _run(["machinectl", "show", machine])[0] != 0:
                    break
                time.sleep(1)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
        if process.returncode not in (None, 0):
            _log(f"nspawn exited with {process.returncode}; log={log_path}")
        _cleanup_stale_nspawn_mounts()


def _find_nspawn_root(machine):
    """Return the root directory reported by machinectl."""
    rc, out, _ = _run(["machinectl", "show", machine, "-p", "RootDirectory"])
    if rc == 0 and "=" in out:
        return out.split("=", 1)[1].strip()
    return ""


def _rpios_can_execute_arm64():
    """Return an actionable reason when ARM64 nspawn cannot run locally."""
    if os.uname().machine in ("aarch64", "arm64"):
        return ""
    if shutil.which("qemu-aarch64-static") is None and shutil.which("qemu-aarch64") is None:
        return (
            "the cached Raspberry Pi OS image is ARM64 but this host is "
            f"{os.uname().machine}; install qemu-user-static/binfmt support "
            "or run this test on a Raspberry Pi"
        )
    registered = any(
        Path(path).exists()
        for path in (
            "/proc/sys/fs/binfmt_misc/qemu-aarch64",
            "/proc/sys/fs/binfmt_misc/arm64",
            "/proc/sys/fs/binfmt_misc/ARM64",
        )
    )
    if not registered:
        return (
            "qemu-aarch64 is installed, but ARM64 binfmt is not registered; "
            "enable qemu-user-static/binfmt or run this test on a Raspberry Pi"
        )
    return ""


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
    """Tier 2 needs root and systemd-nspawn; skip with a clear reason."""
    if os.geteuid() != 0:
        pytest.skip("Tier 2 (real RPi OS image) needs root for losetup/systemd-nspawn")
    for tool in ("systemd-nspawn", "losetup", "machinectl"):
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
