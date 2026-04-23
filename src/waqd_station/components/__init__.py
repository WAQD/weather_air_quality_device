"""
This module contains all interfaces to HW (OS, sensors, etc.) and online interface functions.
Settings need to be already set up for usage.
"""

from waqd.components.sensor_base import (
    SENSOR_EXTERIOR_TYPE,
    SENSOR_INTERIOR_TYPE,
    BarometricSensor,
    CO2Sensor,
    DustSensor,
    HumiditySensor,
    LightSensor,
    SensorComponent,
    TempSensor,
    TvocSensor,
    WAQDRemoteSensor,
    WAQDRemoteStation,
)
from waqd.components.weather import OpenMeteo, WeatherProvider

from .display import Display
from .events import EventHandler
from .power import ESaver
from .sensors import (
    BH1750,
    BME280,
    BMP280,
    CCS811,
    DHT22,
    GP2Y1010AU0F,
    MH_Z19,
    SR501,
)
from .sound import SoundInterface, SoundVLC
from .speech import TextToSpeach
from .updater import OnlineUpdater
from .website_service import WAQDDeviceClient

__all__ = [
    "Display",
    "EventHandler",
    "OpenMeteo",
    "WeatherProvider",
    "ESaver",
    "BH1750",
    "BME280",
    "BMP280",
    "CCS811",
    "DHT22",
    "GP2Y1010AU0F",
    "MH_Z19",
    "SR501",
    "BarometricSensor",
    "CO2Sensor",
    "DustSensor",
    "HumiditySensor",
    "LightSensor",
    "WAQDRemoteSensor",
    "WAQDRemoteStation",
    "SensorComponent",
    "TempSensor",
    "TvocSensor",
    "SoundInterface",
    "SoundVLC",
    "TextToSpeach",
    "OnlineUpdater",
    "WAQDDeviceClient",
    "SENSOR_EXTERIOR_TYPE",
    "SENSOR_INTERIOR_TYPE",
]
