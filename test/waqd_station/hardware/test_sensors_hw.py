"""Hardware-integration tests for the physical sensors.

These run on the Raspberry Pi target with real sensors wired up
(``WAQD_HW_CONNECTED=1``). They reuse the same structure as the mock-based
``test/waqd_station/components/test_sensors.py`` (ComponentRegistry + Settings
+ tuned ``MEASURE_POINTS``/``UPDATE_TIME`` + a stabilization sleep) but assert
**ranges** instead of exact mock constants, since real sensors fluctuate.

Each test is tagged ``@pytest.mark.hardware`` and the directory-level
``conftest.py`` skips everything unless ``WAQD_HW_CONNECTED`` is set, so these
are deselected by the x86 CI's ``-m "not hardware"`` filter.
"""

import time

import pytest

from waqd_station.app.component_reg import ComponentRegistry
from waqd_station.components.sensors import (
    BME280,
    BMP280,
    CCS811,
    DHT22,
    MH_Z19,
)
from waqd_station.settings import Settings


# --- Sanity bounds for live sensor reads -------------------------------------
# Real values drift, so assert plausible ranges rather than exact numbers.
DHT_TEMP_RANGE = (10.0, 50.0)  # degC
DHT_HUM_RANGE = (5.0, 95.0)  # % RH
BME_TEMP_RANGE = (0.0, 50.0)
BME_HUM_RANGE = (5.0, 95.0)
BME_PRESSURE_RANGE = (900.0, 1100.0)  # hPa, sea-level adjusted
BMP_TEMP_RANGE = (0.0, 50.0)
BMP_PRESSURE_RANGE = (900.0, 1100.0)
CO2_RANGE = (350.0, 2500.0)  # ppm, ambient to stuffy indoor
TVOC_RANGE = (0.0, 2000.0)  # ppb


def _stabilize(sensor, measure_points: int, update_time: float) -> None:
    """Wait for the moving average to fill, mirroring the mock test pattern."""
    time.sleep(update_time * (measure_points + 1))


@pytest.mark.hardware
@pytest.mark.slow
def test_dht22_hw(base_fixture, target_mockup_fixture):
    settings = Settings(base_fixture.testdata_path / "integration")
    comps = ComponentRegistry(settings)
    measure_points = 2
    DHT22.MEASURE_POINTS = measure_points
    DHT22.UPDATE_TIME = 1
    sensor = DHT22(pin=22, components=comps, settings=settings)

    time.sleep(1)
    assert sensor.is_alive
    assert sensor.is_ready

    _stabilize(sensor, measure_points, sensor.UPDATE_TIME)
    temp = sensor.get_temperature().magnitude
    hum = sensor.get_humidity().magnitude
    assert DHT_TEMP_RANGE[0] <= temp <= DHT_TEMP_RANGE[1], f"DHT22 temp {temp}°C out of range"
    assert DHT_HUM_RANGE[0] <= hum <= DHT_HUM_RANGE[1], f"DHT22 humidity {hum}% out of range"


@pytest.mark.hardware
@pytest.mark.slow
def test_ccs811_hw(base_fixture, target_mockup_fixture):
    settings = Settings(base_fixture.testdata_path / "integration")
    measure_points = 2
    CCS811.MEASURE_POINTS = measure_points
    comps = ComponentRegistry(settings)
    sensor = CCS811(comps, settings)

    time.sleep(1)
    assert sensor.is_alive
    assert sensor.is_ready

    _stabilize(sensor, measure_points, sensor.UPDATE_TIME)
    tvoc = sensor.get_tvoc().magnitude
    co2 = sensor.get_co2().magnitude
    assert TVOC_RANGE[0] <= tvoc <= TVOC_RANGE[1], f"CCS811 tvoc {tvoc} ppb out of range"
    assert CO2_RANGE[0] <= co2 <= CO2_RANGE[1], f"CCS811 co2 {co2} ppm out of range"


@pytest.mark.hardware
@pytest.mark.slow
def test_mh_z19_hw(base_fixture, target_mockup_fixture, mocker):
    # On x86 this would be skipped by the directory gate; on the target it
    # drives the real /dev/serialMH-Z19 device via the mh_z19 subprocess helper.
    from waqd.base.system import RuntimeSystem

    assert RuntimeSystem().is_target_system, "MH-Z19 hardware test requires the target device"
    settings = Settings(base_fixture.testdata_path / "integration")
    MH_Z19.MEASURE_POINTS = 2
    sensor = MH_Z19(settings)

    time.sleep(1)
    assert sensor.is_alive
    assert sensor.is_ready

    # mh_z19 spawns a python process per read; give it room.
    _stabilize(sensor, MH_Z19.MEASURE_POINTS, sensor.UPDATE_TIME)
    co2 = sensor.get_co2().magnitude
    assert CO2_RANGE[0] <= co2 <= CO2_RANGE[1], f"MH-Z19 co2 {co2} ppm out of range"


@pytest.mark.hardware
@pytest.mark.slow
def test_bme280_hw(base_fixture, target_mockup_fixture):
    settings = Settings(base_fixture.testdata_path / "integration")
    measure_points = 2
    BME280.UPDATE_TIME = 1
    BME280.MEASURE_POINTS = measure_points
    comps = ComponentRegistry(settings)
    sensor = BME280(comps, settings)

    time.sleep(1)
    assert sensor.is_alive
    assert sensor.is_ready

    _stabilize(sensor, sensor.MEASURE_POINTS, sensor.UPDATE_TIME)
    temp = sensor.get_temperature().magnitude
    hum = sensor.get_humidity().magnitude
    pressure = sensor.get_pressure().magnitude
    assert BME_TEMP_RANGE[0] <= temp <= BME_TEMP_RANGE[1], f"BME280 temp {temp}°C out of range"
    assert BME_HUM_RANGE[0] <= hum <= BME_HUM_RANGE[1], f"BME280 humidity {hum}% out of range"
    assert BME_PRESSURE_RANGE[0] <= pressure <= BME_PRESSURE_RANGE[1], (
        f"BME280 pressure {pressure} hPa out of range"
    )


@pytest.mark.hardware
@pytest.mark.slow
def test_bmp280_hw(base_fixture, target_mockup_fixture):
    settings = Settings(base_fixture.testdata_path / "integration")
    measure_points = 2
    BMP280.MEASURE_POINTS = measure_points
    BMP280.UPDATE_TIME = 1
    comps = ComponentRegistry(settings)
    sensor = BMP280(comps, settings)

    time.sleep(1)
    assert sensor.is_alive
    assert sensor.is_ready

    _stabilize(sensor, measure_points, sensor.UPDATE_TIME)
    temp = sensor.get_temperature().magnitude
    pressure = sensor.get_pressure().magnitude
    assert BMP_TEMP_RANGE[0] <= temp <= BMP_TEMP_RANGE[1], f"BMP280 temp {temp}°C out of range"
    assert BMP_PRESSURE_RANGE[0] <= pressure <= BMP_PRESSURE_RANGE[1], (
        f"BMP280 pressure {pressure} hPa out of range"
    )
