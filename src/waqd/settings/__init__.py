# use constants in class, so they don't need to be separately accessed
# constants for option names - value (ini name) should be very similar to internal string
# general
LANG = "lang"
LANG_GERMAN = "de"
LANG_ENGLISH = "en"
LANG_HUNGARIAN = "hu"

SOUND_ENABLED = "sound_enabled"
STARTUP_JINGLE = "startup_jingle"  # sound played on startup, if sound_enabled is True
EVENTS_ENABLED = "events_enabled"
# general hw
DISPLAY_TYPE = "display_type"
DISP_TYPE_RPI = "RPI_TD"  # original 7" rpi touch display
DISP_TYPE_WAVESHARE_5_LCD = "Waveshare_LCD"  # Waveshare 5" touch display
DISP_INVERTED = "display_inverted"

DHT_22_DISABLED = 0
DHT_22_PIN = "dht_22_pin"  # on if not DHT_22_DISABLED (0)
BMP_280_ENABLED = "bmp_280_enabled"
BME_280_ENABLED = "bme_280_enabled"
MOTION_SENSOR_PIN = "motion_sensor_pin"
WAVESHARE_DISP_BRIGHTNESS_PIN = "waveshare_disp_brightness_pin"
CCS811_ENABLED = "ccs811_enabled"
MH_Z19_ENABLED = "mh_z19_enabled"
MH_Z19_VALUE_OFFSET = "mh_z19_value_offset"
LOG_SENSOR_DATA = "log_sensor_data"

# WAQD Website
USER_API_KEY = "user_api_key"
# save mac address of the device for identification (could change, but still the saved one)
MAC_ADDRESS = "mac_address"

# Local remote mode
REMOTE_MODE_URL = "remote_mode_url"
REMOTE_API_KEY = "remote_api_key"

# updater
AUTO_UPDATER_ENABLED = "auto_updater_enabled"
UPDATER_USER_BETA_CHANNEL = "updater_use_beta_channel"

# saved sensor values
LAST_TEMP_C_OUTSIDE = "last_temp_outside_value"  # TODO write

# gui
FORECAST_BG = "forecast_background"
INTERIOR_BG = "interior_background"
THEME_COLOR = "theme_color"

# energy saving
NIGHT_MODE_BEGIN = "night_mode_begin"
NIGHT_MODE_END = "night_mode_end"
BRIGHTNESS = "brightness"
MOTION_SENSOR_ENABLED = (
    "motion_sensor_enabled"  # redundant with pin number, this is for user settings
)
DAY_STANDBY_TIMEOUT = "day_standby_timeout"
NIGHT_STANDBY_TIMEOUT = "night_standby_timeout"
# forecast
LOCATION_NAME = "location"  # only for display and search purposes
LOCATION_LONGITUDE = "location_long"
LOCATION_LATITUDE = "location_lat"
LOCATION_ALTITUDE_M = "last_altitude_value"
LOCATION_STATE = "location_state"  # e.g. state, province, region
LOCATION_COUNTRY_CODE = "location_country_code"

OW_API_KEY = "open_weather_api_key"

# import at the end, to avoid circular imports
from waqd.settings.settings import Settings

__all__ = ["Settings"]
