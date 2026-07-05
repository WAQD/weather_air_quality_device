

from waqd.settings.settings import Settings as BaseSettings
from waqd_station.settings import (
    AUTO_UPDATER_ENABLED,
    BME_280_ENABLED,
    BMP_280_ENABLED,
    BMX280_TEMP_OFFSET_C,
    BRIGHTNESS,
    CCS811_ENABLED,
    DAY_STANDBY_TIMEOUT,
    DHT_22_DISABLED,
    DHT_22_PIN,
    DISP_INVERTED,
    DISP_TYPE_RPI,
    DISPLAY_TYPE,
    EVENTS_ENABLED,
    FORECAST_BG,
    INTERIOR_BG,
    LANG,
    LANG_GERMAN,
    LAST_TEMP_C_OUTSIDE,
    LOCATION_ALTITUDE_M,
    LOCATION_COUNTRY_CODE,
    LOCATION_LATITUDE,
    LOCATION_LONGITUDE,
    LOCATION_NAME,
    LOCATION_STATE,
    LOG_SENSOR_DATA,
    MAC_ADDRESS,
    MH_Z19_ENABLED,
    MH_Z19_VALUE_OFFSET,
    MOTION_SENSOR_ENABLED,
    MOTION_SENSOR_PIN,
    NIGHT_MODE_BEGIN,
    NIGHT_MODE_END,
    NIGHT_STANDBY_TIMEOUT,
    OW_API_KEY,
    REMOTE_API_KEY,
    REMOTE_MODE_URL,
    SOUND_ENABLED,
    STARTUP_JINGLE,
    THEME_COLOR,
    UPDATER_USER_BETA_CHANNEL,
    USER_API_KEY,
    WAVESHARE_DISP_BRIGHTNESS_PIN,
)


class Settings(BaseSettings):
 
    # internal constants
    _THEMING_SECTION_NAME = "GUI"
    _GENERAL_SECTION_NAME = "General"
    _ENERGY_SECTION_NAME = "Energy"
    _LOCATION_SECTION_NAME = "Location"
    _REMOTE_SECTION_NAME = "User"
    _SENSOR_SECTION_NAME = "Sensors"

    def _init_values(self):
        ### default setting values ###
        from waqd.base.network import Network
        self._values = {
            self._GENERAL_SECTION_NAME: {
                LANG: LANG_GERMAN,
                SOUND_ENABLED: False,
                EVENTS_ENABLED: True,
                DISPLAY_TYPE: DISP_TYPE_RPI,
                DISP_INVERTED: False,
                WAVESHARE_DISP_BRIGHTNESS_PIN: 18,
                AUTO_UPDATER_ENABLED: True,
                UPDATER_USER_BETA_CHANNEL: False,
                LAST_TEMP_C_OUTSIDE: 23.5,
                STARTUP_JINGLE: True,
                MAC_ADDRESS: Network.get_mac_address(),
            },
            self._THEMING_SECTION_NAME: {
                INTERIOR_BG: "background_s8.jpg",
                FORECAST_BG: "background_s9.jpg",
                THEME_COLOR: "purple"
            },
            self._ENERGY_SECTION_NAME: {
                NIGHT_MODE_BEGIN: "22:00",
                NIGHT_MODE_END: "07:00",
                BRIGHTNESS: 90,
                DAY_STANDBY_TIMEOUT: 600,
                NIGHT_STANDBY_TIMEOUT: 600,
            },
            self._LOCATION_SECTION_NAME: {
                LOCATION_NAME: "",
                LOCATION_COUNTRY_CODE: "",
                LOCATION_LATITUDE: 0.0,
                LOCATION_LONGITUDE: 0.0,
                LOCATION_ALTITUDE_M: 400.0,
                LOCATION_STATE: "",
            },
            self._REMOTE_SECTION_NAME: {
                REMOTE_MODE_URL: "",
                REMOTE_API_KEY: "",
            },
            self._SENSOR_SECTION_NAME: {
                DHT_22_PIN: DHT_22_DISABLED,  # if not disabled, the pin number is used
                BME_280_ENABLED: False,
                BMP_280_ENABLED: False,
                CCS811_ENABLED: False,
                MH_Z19_ENABLED: False,
                MH_Z19_VALUE_OFFSET: 0,
                BMX280_TEMP_OFFSET_C: 0.0,
                MOTION_SENSOR_ENABLED: True,
                MOTION_SENSOR_PIN: 23,
                LOG_SENSOR_DATA: True,
            },
            self._SECRET_SECTION_NAME: {
                USER_API_KEY: "",
                OW_API_KEY: "",
            },
        }
