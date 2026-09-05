"""Tier 2: install into the OFFICIAL Raspberry Pi OS image and verify.

This is the high-fidelity tier. It mounts the real image (no unofficial base
image) and boots it with ``systemd-nspawn --boot``, which gives a genuine PID 1
- so the installer's ``reboot`` is real and we can assert the device comes back
up with the app running.

Slow (needs the image download + apt + pipx, and qemu emulation on x64), so it
is marked ``slow`` in addition to ``os_test``. Intended for per-release runs on
a dev machine, not CI.

Prerequisites:
    sudo ./script/os_test/run_nspawn.sh <image.img>   # in one terminal
    WAQD_OS_TEST=1 pdm run pytest test/os_test/test_install_rpios.py -q --timeout=3600

The tests attach to an already-running machine rather than booting one, because
booting needs an interactive root session that pytest does not have.
"""

import re
import os
import time

import pytest

from .conftest import TARGET_USER

pytestmark = [pytest.mark.os_test, pytest.mark.slow]


@pytest.fixture(scope="module")
def sut(rpios_machine):
    """Use the automatically managed Raspberry Pi OS machine."""
    return rpios_machine


@pytest.fixture(scope="module")
def installed(sut):
    if os.getenv("WAQD_OS_TEST_SKIP_INSTALL", "0") == "1":
        print("Reusing existing RPi OS installation; installer skipped", flush=True)
        return 0, "installer skipped by WAQD_OS_TEST_SKIP_INSTALL=1", ""
    return sut.install(timeout=3600)


def test_complete_installation_and_reboot(sut, installed, assert_probe):
    """Install once, validate Pi-specific state, reboot, and validate runtime."""
    rc, out, err = installed
    assert rc == 0, f"installer failed with {rc}\nstdout:\n{out}\nstderr:\n{err}"

    # Includes the Pi-only checks (splash, hw_access) that Tier 1 skips.
    passed, skipped = assert_probe(sut, checks=("all",), timeout=600)
    # On the real image nothing should be skipped for lack of Pi hardware.
    assert "splash" in passed, "splash check did not run on the real image"
    assert "hw_access" in passed, "hw_access check did not run on the real image"

    # The installer is run with WAQD_SKIP_REBOOT=1 by the shared harness, so
    # verify that it requested a reboot before performing it under pytest's
    # control.
    rc, out, _ = sut.exec(["cat", f"/home/{TARGET_USER}/.waqd/reboot_requested"])
    assert rc == 0, "installer did not request a reboot"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", out.strip()), out

    # The real Tier 2 test: reboot and prove the app respawns and serves the
    # UI. `waqd-start` is an `until` loop in the LXDE autostart, so after a
    # reboot the app must be running again without manual intervention.
    sut.reboot()

    deadline_ok = False
    for _ in range(30):
        rc, out, _ = sut.exec(["pgrep", "-f", "waqd-start"], timeout=60)
        if rc == 0 and out.strip():
            deadline_ok = True
            break
        time.sleep(5)
    assert deadline_ok, "waqd-start did not respawn after reboot"

    assert_probe(sut, checks=("runtime", "autostart", "bin"), timeout=600)
