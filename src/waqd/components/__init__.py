"""
This module contains all interfaces to HW (OS, sensors, etc.) and online interface functions.
Settings need to be already set up for usage.
"""

from waqd.components.display import Display
from waqd.components.events import EventHandler
from waqd.components.website_service import WAQDDeviceClient
from waqd.components.power import ESaver
from waqd.components.sensors import (
    BH1750,
    BME280,
    BMP280,
    CCS811,
    DHT22,
    GP2Y1010AU0F,
    MH_Z19,
    SR501,
    BarometricSensor,
    CO2Sensor,
    DustSensor,
    HumiditySensor,
    LightSensor,
    SensorComponent,
    TempSensor,
    TvocSensor,
    WAQDRemoteSensor,
)
from waqd.components.sound import SoundInterface, SoundVLC
from waqd.components.speech import TextToSpeach
from waqd.components.updater import OnlineUpdater
from waqd.components.weather import OpenMeteo, OpenWeatherMap, WeatherProvider

__all__ = [
    "Display",
    "EventHandler",
    "OpenWeatherMap",
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
    "SensorComponent",
    "TempSensor",
    "TvocSensor",
    "SoundInterface",
    "SoundVLC",
    "TextToSpeach",
    "OnlineUpdater",
    "WAQDDeviceClient",
]