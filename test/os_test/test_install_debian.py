"""Tier 1: install into a plain Debian trixie container and verify the OS state.

Covers the ~85% of the installer that is Debian-specific rather than
Pi-specific. Runs natively on x64, so it is fast enough to run per release.

    WAQD_OS_TEST=1 pdm run pytest test/os_test/test_install_debian.py -s --timeout=1800
"""

import re
import os
from pathlib import Path

import pytest

from .conftest import TARGET_USER, ContainerSUT, _run

pytestmark = pytest.mark.os_test

IMAGE = "waqd-os-test:trixie"
BASE_IMAGE = "waqd-os-base:trixie"
CONTAINER = "waqd-os-test-debian"


def _current_version(repo_root: Path) -> str:
    """Read the version the installer will use, straight from pyproject.toml."""
    for line in (repo_root / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise AssertionError("no version found in pyproject.toml")


@pytest.fixture(scope="module")
def sut(repo_root, container_cli, require_docker):
    """Build the Debian image once per module and run the installer in it."""
    print(f"\nUsing container runtime: {container_cli}", flush=True)
    rebuild = os.getenv("WAQD_OS_TEST_REBUILD", "").strip() == "1"
    base_exists = _run([container_cli, "image", "exists", BASE_IMAGE])[0] == 0
    if rebuild or not base_exists:
        reason = "forced by WAQD_OS_TEST_REBUILD=1" if rebuild else "base image not present"
        print(f"Building {BASE_IMAGE} ({reason}); cached layers are enabled", flush=True)
        _run(
            [
                container_cli,
                "build",
                "-t",
                BASE_IMAGE,
                "--target",
                "waqd-os-base",
                "-f",
                "test/os_test/Dockerfile.debian-trixie",
                ".",
            ],
            cwd=repo_root,
            check=True,
            timeout=1800,
        )
    # Always resolve the source stage so edits to the installer are visible.
    # Point the Dockerfile at the separately tagged base image explicitly;
    # this prevents Podman from reevaluating the apt stage during this build.
    print(f"Building {IMAGE} from cached {BASE_IMAGE}; source layers only", flush=True)
    _run(
        [
            container_cli,
            "build",
            "--layers",
            "-t",
            IMAGE,
            "--target",
            "waqd-os-test",
            "--build-arg",
            f"OS_BASE_IMAGE={BASE_IMAGE}",
            "-f",
            "test/os_test/Dockerfile.debian-trixie",
            ".",
        ],
        cwd=repo_root,
        check=True,
        timeout=1800,
    )
    print("Container image built; starting test container", flush=True)
    system = ContainerSUT.start(IMAGE, CONTAINER, runtime=container_cli)
    try:
        yield system
    finally:
        system.stop()


@pytest.fixture(scope="module")
def installed(sut, repo_root):
    """Run the installer once and return (returncode, stdout, stderr)."""
    print("Running installer inside container", flush=True)
    return sut.install()


def test_complete_installation(sut, installed, assert_probe, repo_root):
    """Run the expensive installer once and validate the complete result."""
    rc, out, err = installed
    assert rc == 0, f"installer failed with {rc}\nstdout:\n{out}\nstderr:\n{err}"

    version = _current_version(repo_root)
    assert_probe(
        sut,
        checks=(
            "autostart",
            "bin",
            "pipx",
            "lightdm",
            "screensaver",
            "udev",
            "apt_conf",
            "audio",
            "reboot",
        ),
        version=version,
    )

    # WAQD_SKIP_REBOOT must leave the marker instead of rebooting.
    rc, out, _ = sut.exec(["cat", f"/home/{TARGET_USER}/.waqd/reboot_requested"])
    assert rc == 0, "installer did not request a reboot"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", out.strip()), out

    # The shims prove the installer reached Pi-specific code paths.
    rc, out, _ = sut.exec(["cat", "/var/log/waqd-shims.log"])
    assert rc == 0
    assert "raspi-config" in out, "installer never called raspi-config"

    # Re-run the installer in the same container to verify idempotency. This
    # is intentionally part of this test: the container and initial install
    # are shared by all assertions, rather than repeated by separate tests.
    autostart_path = f"/home/{TARGET_USER}/.config/lxsession/rpd-x/autostart"
    before = sut.exec(["cat", autostart_path])[1]
    rc, out, err = sut.install()
    assert rc == 0, f"second install failed with {rc}\n{out}\n{err}"
    after = sut.exec(["cat", autostart_path])[1]
    assert before == after, (
        "second install changed the autostart file:\n"
        f"--- before ---\n{before}\n--- after ---\n{after}"
    )
    assert_probe(sut, checks=("all",), version=version)

    # Upgrade the package in the same container and verify that the autostart
    # entry points to the new pipx environment rather than the old version.
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    next_version = ".".join(parts)
    sut.exec(
        [
            "bash",
            "-c",
            f"cd /waqd && sed -i '0,/^version = /c\\version = \"{next_version}\"' pyproject.toml "
            f"&& grep -m1 '^version = ' pyproject.toml",
        ],
        check=True,
    )
    rc, out, err = sut.install()
    assert rc == 0, f"upgrade install failed with {rc}\n{out}\n{err}"
    autostart = sut.exec(["cat", autostart_path])[1]
    assert f"waqd.{next_version}" in autostart, (
        f"autostart does not reference the new version {next_version}:\n{autostart}"
    )
    assert f"waqd.{version}\n" not in autostart, (
        f"autostart still references the old version {version}:\n{autostart}"
    )
    assert_probe(sut, checks=("autostart", "bin", "pipx"), version=next_version)
