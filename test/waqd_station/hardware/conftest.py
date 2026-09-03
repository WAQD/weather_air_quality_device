"""Hardware-integration test gating for ``test/waqd_station/hardware/``.

These tests drive the *real* sensor drivers on a Raspberry Pi with physical
sensors wired up. They are skipped by default and only run when the
``WAQD_HW_CONNECTED`` environment variable is set to a truthy value (e.g.
``WAQD_HW_CONNECTED=1``). This is the secondary safety net on top of the
``@pytest.mark.hardware`` marker, which the x86 CI uses to deselect the whole
directory via ``-m "not hardware"``.

On the target Raspberry Pi (``aarch64``) the root ``test/conftest.py`` does NOT
load the ``test/mock/`` stubs, so the real ``board`` / ``busio`` /
``adafruit_*`` / ``RPi.GPIO`` drivers are imported — exactly what these tests
need. On x86 the mocks would be loaded and these tests would falsely "pass",
which is why the env-var gate exists.
"""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip every test collected under this directory unless HW is connected."""
    hw_connected = bool(os.getenv("WAQD_HW_CONNECTED", "").strip())
    skip_hw = pytest.mark.skip(
        reason="set WAQD_HW_CONNECTED=1 on a Raspberry Pi with sensors wired up to run hardware tests",
    )
    if not hw_connected:
        for item in items:
            # Only skip tests that live in this directory; the hook is scoped
            # to the directory by pytest's conftest inheritance, but be explicit.
            if "hardware" in item.fspath.strpath:
                item.add_marker(skip_hw)
