import json
from pathlib import Path
import shutil
import tempfile
import time
from datetime import datetime

from freezegun import freeze_time

from waqd_station.app.component_reg import ComponentRegistry
from waqd.base.component_ctrl import ComponentController
from waqd.base.file_logger import Logger
from waqd_station.components.events import (EventHandler, get_time_of_day,
                                    parse_event_file, write_events_file)
from waqd_station.settings import NIGHT_MODE_BEGIN, NIGHT_MODE_END, SOUND_ENABLED, Settings

def test_parser(base_fixture, target_mockup_fixture):
    settings = Settings(base_fixture.testdata_path / "integration")
    settings.set(SOUND_ENABLED, True)
    events = parse_event_file(base_fixture.testdata_path / "events" / "events.json")
    assert events
    assert events[0].name == "Daily Greeting"
    assert events[1].name == "Christmas1"
    temp_file = tempfile.gettempdir() + "/eventsTest.json"
    write_events_file(Path(temp_file), events)
    with open(temp_file) as fp:
        events_read = json.load(fp)
    assert events_read.get("events")[0].get("name") == "Daily Greeting"
    assert events_read.get("events")[1].get("name") == "Christmas1"


def test_daily_greeting(base_fixture, target_mockup_fixture, monkeypatch):

    with freeze_time(datetime(2020, 12, 29, 22, 59, 45), tick=True) as frozen:
        settings = Settings(base_fixture.testdata_path / "integration")
        settings.set(NIGHT_MODE_BEGIN, 22)
        settings.set(NIGHT_MODE_END, 0)
        settings.set(SOUND_ENABLED, True)
        comp_ctrl = ComponentController(settings, ComponentRegistry)
        Logger().info("Start")
        comps = comp_ctrl.components
        comps.energy_saver
        ev = EventHandler(comps, "en", "00:00")
        t = get_time_of_day()

        current_date_time = datetime.now()
        settings._logger.info(current_date_time)
        assert t
        while not ev._scheduler:
            time.sleep(1)
        comps.motion_detection_sensor._motion_detected = 5

        time.sleep(20)

        #comps.motion_detection_sensor._motion_detected = 0
        #time.sleep(30)

        # TODO implement


def test_event_scheduler(base_fixture, target_mockup_fixture, monkeypatch):
    # Copy the event file to the temp dir
    config_dir = Path(tempfile.gettempdir()) / "waqd_test"
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(base_fixture.testdata_path / "events/events.json", config_dir / "events.json")

    with freeze_time("2020-12-23 06:29:57+00:00", tick=True) as frozen:
        settings = Settings(base_fixture.testdata_path / "integration")
        settings.set(NIGHT_MODE_END, "07:30")
        settings.set(SOUND_ENABLED, True)
        comp_ctrl = ComponentController(settings, ComponentRegistry)
        Logger().info("Start")
        comps = comp_ctrl.components
        comps.energy_saver

        ev = EventHandler(comps, "de", "07:30")
        t = get_time_of_day()

        current_date_time = datetime.now()
        settings._logger.info(current_date_time)
        assert t
        while not ev._scheduler:
            time.sleep(1)
        comps.motion_detection_sensor._motion_detected = 1
        time.sleep(8)

        comps.motion_detection_sensor._motion_detected = 0
        current_date_time = datetime.now()
        time.sleep(10)

    with freeze_time("2020-12-23 22:59:57+00:00", tick=True):
        time.sleep(4)
        comps.motion_detection_sensor._motion_detected = 1
        time.sleep(1)
        comps.motion_detection_sensor._motion_detected = 0

    with freeze_time("2020-12-24 06:29:57+00:00", tick=True):
        print(ev._scheduler.get_jobs()[1].next_run_time)
        time.sleep(4)
        comps.motion_detection_sensor._motion_detected = 1
        time.sleep(10)
        print(ev._scheduler.get_jobs()[1].next_run_time)

    with freeze_time("2020-12-25 06:59:45", tick=True):
        time.sleep(4)
        comps.motion_detection_sensor._motion_detected = 1
        time.sleep(6)

    with freeze_time("2020-12-24 22:59:57", tick=True):
        time.sleep(5)
        t = get_time_of_day()
        assert t

    with freeze_time("2020-12-25 23:59:58", tick=True):
        time.sleep(5)
        t = get_time_of_day()
        assert t

