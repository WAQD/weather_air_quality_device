import os
import platform
import sys
from pathlib import Path
from tempfile import gettempdir
import shutil
import pytest


class PathSetup:
    def __init__(self):
        self.test_path = Path(os.path.dirname(__file__))
        self.base_path = self.test_path.parent
        self.testdata_path = self.test_path / "testdata"


def load_mocks():
    paths = PathSetup()
    mockup_path = paths.test_path / "mock"
    sys.path = [str(mockup_path)] + sys.path
    os.environ["PYTHONPATH"] = str(paths.test_path / "mock")


# Load hardware mocks before importing any module that does target-only imports
# (e.g. ``nmcli``, ``board``, ``RPi.GPIO``) at module level, otherwise collection fails.
if platform.machine() not in ("aarch64", "armv7l", "armv6l", "armv8l"):
    load_mocks()


import waqd

waqd.DEBUG_LEVEL = 1
import waqd.base.file_logger
import waqd.base.system
import waqd.base.network
import waqd


def is_ci_job():
    """Test runs in CI environment"""
    if os.getenv("GITHUB_WORKSPACE"):
        return True
    return False


@pytest.fixture
def target_mockup_fixture():
    load_mocks()


@pytest.fixture
def base_fixture(request):
    # yield "base_fixture"  # return after setup
    paths = PathSetup()
    waqd.user_config_dir = Path(gettempdir()) / "waqd_test"
    shutil.rmtree(waqd.user_config_dir, ignore_errors=True)

    def teardown():
        # reset singletons
        waqd.base.file_logger.Logger._instance = None
        waqd.base.system.RuntimeSystem._instance = None
        waqd.base.network.Network._instance = None
        os.environ["PYTHONPATH"] = ""

    request.addfinalizer(teardown)

    return paths


def mock_run_on_non_target(mocker):
    class Detector:
        class board:
            any_raspberry_pi = False
            id = "NOT_THE_TARGET"

        class chip:
            id = "arch"

    mocker.patch("adafruit_platformdetect.Detector", Detector)


def mock_run_on_target(mocker):
    load_mocks()
    from target_pkgs.adafruit_platformdetect import Detector

    mocker.patch("adafruit_platformdetect.Detector", Detector)
    # need to patch RPi.GPIO - only installs on Linux
    if platform.system() == "Linux" and not platform.machine() in [
        "aarch64",
        "armv7l",
    ]:  # don't mock on RPi
        # mock_rpi_gpio = mocker.Mock()
        from target_pkgs.RPi import GPIO

        mocker.patch("RPi.GPIO", GPIO)
    mock_plaftorm = mocker.Mock()
    mock_plaftorm.return_value = "Linux"
    mocker.patch("platform.system", mock_plaftorm)
