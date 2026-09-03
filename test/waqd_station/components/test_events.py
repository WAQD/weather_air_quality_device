import json
from pathlib import Path
import shutil
import tempfile
import time
import waqd_station
from datetime import datetime

from freezegun import freeze_time

from waqd_station.app.component_reg import ComponentRegistry
from waqd.base.component_ctrl import ComponentController
from waqd.base.file_logger import Logger
from waqd_station.components.events import (
    EventHandler,
    get_time_of_day,
    parse_event_file,
    write_events_file,
)
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
        settings.set(NIGHT_MODE_BEGIN, "22:00")
        settings.set(NIGHT_MODE_END, "00:00")
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
        deadline = time.monotonic() + 5
        while (
            ev._scheduler is None or not ev._scheduler.get_jobs()
        ) and time.monotonic() < deadline:
            time.sleep(0.05)
        comps.motion_detection_sensor._motion_detected = 5

        time.sleep(20)
        ev.stop()

        # comps.motion_detection_sensor._motion_detected = 0
        # time.sleep(30)

        # TODO implement


def test_event_scheduler(base_fixture, target_mockup_fixture, monkeypatch):
    # Copy the event file to the temp dir
    config_dir = Path(tempfile.gettempdir()) / "waqd_test"
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        base_fixture.testdata_path / "events/events.json", config_dir / "events.json"
    )
    waqd_station.user_config_dir = config_dir

    ev = None
    with freeze_time("2020-12-23 06:29:57+00:00", tick=True):
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
        deadline = time.monotonic() + 5
        while (
            ev._scheduler is None or not ev._scheduler.get_jobs()
        ) and time.monotonic() < deadline:
            time.sleep(0.05)
        # APScheduler does not guarantee list ordering, and direct-execution
        # jobs make the old positional assertion invalid.  Verify the public
        # scheduling result by job names instead.
        deadline = time.monotonic() + 5
        while ev._scheduler is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ev._scheduler is not None
        job_names = {job.name for job in ev._scheduler.get_jobs()}
        assert {"Daily Greeting", "Christmas1", "Christmas2", "Christmas3"} <= job_names

    ev.stop()
