import pytest
from types import SimpleNamespace
from freezegun import freeze_time

from waqd_station.components.power import (
    BRIGHTNESS,
    DAY_STANDBY_TIMEOUT,
    MOTION_SENSOR_ENABLED,
    NIGHT_MODE_BEGIN,
    NIGHT_MODE_BRIGHTNESS,
    NIGHT_MODE_END,
    NIGHT_STANDBY_TIMEOUT,
    NIGHTMODE_WAKEUP_DELTA_BRIGHTNESS,
    STANDBY_BRIGHTNESS,
    ESaver,
)
from waqd_station.settings import Settings
from waqd_station.app.component_reg import ComponentRegistry


@pytest.fixture
def synchronous_esaver(monkeypatch):
    """Construct ESaver without waiting for its production worker loop."""
    monkeypatch.setattr(ESaver, "INIT_WAIT_TIME", 0)
    monkeypatch.setattr(ESaver, "UPDATE_TIME", 1000)

    import pynput.mouse

    monkeypatch.setattr(
        pynput.mouse,
        "Listener",
        lambda **kwargs: SimpleNamespace(start=lambda: None, stop=lambda: None),
    )

    instances = []

    def create(comps, settings):
        instance = ESaver(comps, settings)
        instance.stop()
        instances.append(instance)
        return instance

    yield create
    for instance in instances:
        instance.stop()


def update(esaver):
    """Run one ESaver update synchronously."""
    esaver._ticker_event.clear()
    esaver._set_day_night_mode()


def test_no_standby_if_sensor_is_disabled(base_fixture, synchronous_esaver):
    settings = Settings(base_fixture.testdata_path / "integration")
    settings.set(MOTION_SENSOR_ENABLED, False)
    settings.set(NIGHT_MODE_BEGIN, "23:00")
    settings.set(NIGHT_MODE_END, "05:00")
    settings.set(BRIGHTNESS, 70)

    comps = ComponentRegistry(settings)
    disp = comps.display

    with freeze_time("2019-01-01 12:00:00"):
        energy_saver = synchronous_esaver(comps, settings)
        update(energy_saver)
        assert disp.get_brightness() == settings.get(BRIGHTNESS)


def test_night_mode_startup(base_fixture, synchronous_esaver):
    settings = Settings(base_fixture.testdata_path / "integration")
    settings.set(MOTION_SENSOR_ENABLED, True)
    settings.set(NIGHT_MODE_BEGIN, "23:00")
    settings.set(NIGHT_MODE_END, "05:00")
    settings.set(BRIGHTNESS, 70)
    comps = ComponentRegistry(settings)
    disp = comps.display
    energy_saver = synchronous_esaver(comps, settings)

    with freeze_time("2019-01-01 01:59:59"):
        assert energy_saver._update_thread is not None
        assert not energy_saver.night_mode_active
        assert disp.get_brightness() == 70
        update(energy_saver)
        assert disp.get_brightness() == NIGHT_MODE_BRIGHTNESS
        assert energy_saver.night_mode_active

    with freeze_time("2019-01-01 02:00:01"):
        update(energy_saver)
        assert energy_saver.night_mode_active
        assert disp.get_brightness() == NIGHT_MODE_BRIGHTNESS

    with freeze_time("2019-01-02 04:59:01"):
        update(energy_saver)
        assert energy_saver.night_mode_active
        assert disp.get_brightness() == NIGHT_MODE_BRIGHTNESS


def test_night_mode_enter(base_fixture, synchronous_esaver):
    settings = Settings(base_fixture.testdata_path / "integration")
    settings.set(MOTION_SENSOR_ENABLED, True)
    settings.set(NIGHT_MODE_BEGIN, "23:00")
    settings.set(NIGHT_MODE_END, "05:00")
    settings.set(BRIGHTNESS, 70)

    comps = ComponentRegistry(settings)
    disp = comps.display
    energy_saver = synchronous_esaver(comps, settings)

    with freeze_time("2019-01-01 22:59:59"):
        assert energy_saver._update_thread is not None
        assert not energy_saver.night_mode_active
        assert disp.get_brightness() == 70
        update(energy_saver)
        assert disp.get_brightness() == STANDBY_BRIGHTNESS
        assert not energy_saver.night_mode_active

    with freeze_time("2019-01-01 23:00:01"):
        update(energy_saver)
        assert energy_saver.night_mode_active
        assert disp.get_brightness() == NIGHT_MODE_BRIGHTNESS

    with freeze_time("2019-01-02 04:59:01"):
        update(energy_saver)
        assert energy_saver.night_mode_active
        assert disp.get_brightness() == NIGHT_MODE_BRIGHTNESS


def test_day_mode_enter(base_fixture, synchronous_esaver):
    settings = Settings(base_fixture.testdata_path / "integration")
    settings.set(MOTION_SENSOR_ENABLED, True)
    settings.set(NIGHT_MODE_BEGIN, "22:00")
    settings.set(NIGHT_MODE_END, "05:00")
    settings.set(BRIGHTNESS, 70)

    comps = ComponentRegistry(settings)
    disp = comps.display
    energy_saver = synchronous_esaver(comps, settings)

    with freeze_time("2019-01-01 22:59:59"):
        assert energy_saver._update_thread is not None
        assert 70 == disp.get_brightness()
        update(energy_saver)
        assert disp.get_brightness() == NIGHT_MODE_BRIGHTNESS
        assert energy_saver.night_mode_active

    with freeze_time("2019-01-02 05:00:01"):
        update(energy_saver)
        assert not energy_saver.night_mode_active
        # At the configured wake time the implementation restores normal
        # brightness; standby is entered only after a subsequent idle update.
        assert disp.get_brightness() == settings.get(BRIGHTNESS)

    with freeze_time("2019-01-02 21:59:01"):
        update(energy_saver)
        assert not energy_saver.night_mode_active
        assert disp.get_brightness() == STANDBY_BRIGHTNESS


def test_wake_up_from_night_mode(base_fixture, synchronous_esaver):
    settings = Settings(base_fixture.testdata_path / "integration")

    settings.set(MOTION_SENSOR_ENABLED, True)
    settings.set(NIGHT_MODE_BEGIN, "22:00")
    settings.set(NIGHT_MODE_END, "05:00")
    settings.set(BRIGHTNESS, 70)
    settings.set(NIGHT_STANDBY_TIMEOUT, 0)

    comps = ComponentRegistry(settings)
    disp = comps.display
    energy_saver = synchronous_esaver(comps, settings)

    with freeze_time("2019-01-01 22:59:59"):
        update(energy_saver)
        assert NIGHT_MODE_BRIGHTNESS == disp.get_brightness()
        assert energy_saver.night_mode_active

        comps.motion_detection_sensor._motion_detected = 1
        update(energy_saver)
        assert disp.get_brightness() == 70 - NIGHTMODE_WAKEUP_DELTA_BRIGHTNESS

        comps.motion_detection_sensor._motion_detected = 0
        energy_saver.sleep()
        update(energy_saver)
        assert disp.get_brightness() == NIGHT_MODE_BRIGHTNESS


def test_standby_in_day_mode(base_fixture, synchronous_esaver):
    settings = Settings(base_fixture.testdata_path / "integration")
    settings.set(MOTION_SENSOR_ENABLED, True)
    settings.set(NIGHT_MODE_BEGIN, "22:00")
    settings.set(NIGHT_MODE_END, "05:00")
    settings.set(BRIGHTNESS, 70)
    settings.set(DAY_STANDBY_TIMEOUT, 0)

    comps = ComponentRegistry(settings)
    disp = comps.display

    energy_saver = synchronous_esaver(comps, settings)

    # day
    with freeze_time("2019-01-01 12:59:59"):
        update(energy_saver)
        assert energy_saver.night_mode_active is False
        assert disp.get_brightness() == STANDBY_BRIGHTNESS

    # switch to wake
    comps.motion_detection_sensor._motion_detected = 1
    with freeze_time("2019-01-01 13:00:10"):
        update(energy_saver)
        assert disp.get_brightness() == settings.get(BRIGHTNESS)
        # switch to standby
        comps.motion_detection_sensor._motion_detected = 0
        update(energy_saver)
        assert disp.get_brightness() == STANDBY_BRIGHTNESS
