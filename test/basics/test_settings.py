import os
import tempfile
import shutil
import configparser

from waqd.settings import BRIGHTNESS, DAY_STANDBY_TIMEOUT, DISPLAY_TYPE, LANG, LOCATION_NAME, MOTION_SENSOR_ENABLED, NIGHT_MODE_BEGIN, NIGHT_MODE_END, NIGHT_STANDBY_TIMEOUT, OW_API_KEY
from waqd.settings.settings import Settings


def test_read_from_file(base_fixture):
    sets = Settings(ini_folder=base_fixture.testdata_path / "settings/read")
    assert sets.get(LANG) == "MyLanguage"
    assert sets.get(DISPLAY_TYPE) == "RPI_TD"
    assert sets.get(LOCATION_NAME) == "MyCity"
    assert sets.get(OW_API_KEY) == "456abcd"
    assert sets.get(NIGHT_MODE_BEGIN) == "22:00"
    assert sets.get(NIGHT_MODE_END) == "8:00"
    assert sets.get(BRIGHTNESS) == 70
    assert not sets.get(MOTION_SENSOR_ENABLED)
    assert sets.get(DAY_STANDBY_TIMEOUT) == 30
    assert sets.get(NIGHT_STANDBY_TIMEOUT) == 60


def test_save_to_file(base_fixture):
    # copy testdata to temp
    temp_dir = tempfile.gettempdir()
    temp_ini_path = os.path.join(temp_dir, "config.ini")
    shutil.copy(base_fixture.testdata_path / "settings/write/config.ini", temp_dir)
    sets = Settings(ini_folder=temp_dir)

    lang = "MyLanguage"
    location = "MyCity"
    night_mode_begin = 22
    night_mode_end = 8
    brightness = 70
    motion_sensor_enabled = False
    day_standby_timeout = 30
    night_standby_timeout = 60

    sets.set(LANG, lang)
    sets.set(LOCATION_NAME, location)
    sets.set(NIGHT_MODE_BEGIN, night_mode_begin)
    sets.set(NIGHT_MODE_END, night_mode_end)
    sets.set(BRIGHTNESS, brightness)
    sets.set(MOTION_SENSOR_ENABLED, motion_sensor_enabled)
    sets.set(DAY_STANDBY_TIMEOUT, day_standby_timeout)
    sets.set(NIGHT_STANDBY_TIMEOUT, night_standby_timeout)

    sets.save()

    # read file
    parser = configparser.ConfigParser()
    parser.read(temp_ini_path, encoding="UTF-8")

    # assert set settings
    assert parser.get(sets._GENERAL_SECTION_NAME, LANG) == lang
    assert parser.get(sets._LOCATION_SECTION_NAME, LOCATION_NAME) == location
    assert parser.get(sets._ENERGY_SECTION_NAME, NIGHT_MODE_BEGIN) == str(night_mode_begin)
    assert parser.get(sets._ENERGY_SECTION_NAME, NIGHT_MODE_END) == str(night_mode_end)
    assert parser.get(sets._SENSOR_SECTION_NAME, MOTION_SENSOR_ENABLED) == str(motion_sensor_enabled)
    assert parser.get(sets._ENERGY_SECTION_NAME, DAY_STANDBY_TIMEOUT) == str(day_standby_timeout)
    assert parser.get(sets._ENERGY_SECTION_NAME, NIGHT_STANDBY_TIMEOUT) == str(night_standby_timeout)

    # assert, that original entries remain untouched
    assert parser.get("MyCustomSection", "MyCustomKey") == "123"
    # delete tempfile
    os.remove(temp_ini_path)
