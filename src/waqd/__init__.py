"""
Contains global constants and basic/ui variables.
Should not contain any 3rd party imports!
"""

import datetime
from enum import Enum
import os
from pathlib import Path
from typing import TYPE_CHECKING

from waqd.base.singleton import BorgSingleton

if TYPE_CHECKING:
    from pint import UnitRegistry as PintUnitRegistry

### Global constants ###

### Global Flags and constants ###
# 0: No debug, 1 = logging on, 2: remote debugging on
# 3: wait for remote debugger, 4: quick-load
DEBUG_LEVEL = int(os.getenv("WAQD_DEBUG", "0"))
LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

class WeatherDataProviders(Enum):  # promote to settings, after stable
    OpenWeatherMap = 0
    AccuWeather = 1  # Currently not implemented
    OpenMeteo = 2


WEATHER_DATA_PROVIDER = 2

# paths to find folders
base_path = Path(__file__).absolute().parent
assets_path = base_path.parent / "waqd_assets"


class UnitRegistrySingleton(BorgSingleton["PintUnitRegistry"]):
    @classmethod
    def _create_instance(cls, key: object) -> "PintUnitRegistry":
        from pint import UnitRegistry

        unit_reg = UnitRegistry()
        unit_reg.define("fraction = [] = frac")
        unit_reg.define("percent = 1e-2 frac = %")
        unit_reg.define("ppm = 1e-6 fraction")
        unit_reg.define("ppb = 1e-9 fraction")
        return unit_reg

unit_reg = UnitRegistrySingleton()
