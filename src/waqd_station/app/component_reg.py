import platform

# this allows to use forward declarations to avoid circular imports
from typing import override

import waqd
from waqd.components.sensor_base import WAQDRemoteStation
from waqd.components.weather.open_meteo import OpenMeteo
import waqd_station
from waqd_station.settings import (
    BME_280_ENABLED,
    BMP_280_ENABLED,
    BRIGHTNESS,
    CCS811_ENABLED,
    DHT_22_DISABLED,
    DHT_22_PIN,
    DISPLAY_TYPE,
    EVENTS_ENABLED,
    LANG,
    LAST_TEMP_C_OUTSIDE,
    LOCATION_ALTITUDE_M,
    LOCATION_LATITUDE,
    LOCATION_LONGITUDE,
    LOG_SENSOR_DATA,
    MAC_ADDRESS,
    MH_Z19_ENABLED,
    MOTION_SENSOR_ENABLED,
    MOTION_SENSOR_PIN,
    NIGHT_MODE_END,
    OW_API_KEY,
    REMOTE_API_KEY,
    REMOTE_MODE_URL,
    SOUND_ENABLED,
    USER_API_KEY,
    WAVESHARE_DISP_BRIGHTNESS_PIN,
)

from waqd_station.components import (
    SR501,
    BarometricSensor,
    CO2Sensor,
    Display,
    DustSensor,
    ESaver,
    EventHandler,
    HumiditySensor,
    LightSensor,
    OnlineUpdater,
    WAQDRemoteSensor,
    BMP280,
    DHT22,
    BME280,
    MH_Z19,
    CCS811,
    SoundVLC,
    SoundInterface,
    TempSensor,
    TextToSpeach,
    TvocSensor,
    WeatherProvider,
    WAQDDeviceClient,
    SENSOR_EXTERIOR_TYPE,
    SENSOR_INTERIOR_TYPE,
)
from waqd.base.component_reg import ComponentRegistry as ComponentRegistryBase


class ComponentRegistry(ComponentRegistryBase):
    """
    Abstraction to hold all components, create, stop and get access to them.
    An instance is passed automatically to all components.
    """

    @override
    def _save_cached_values(self):
        """Save values which need to be cached for next start"""
        try:
            if not self.weather_info.is_disabled:
                cw = self.weather_info.get_current_weather()
                if cw:
                    self._settings.set(LAST_TEMP_C_OUTSIDE, cw.temp)
                    self._settings.set(LOCATION_ALTITUDE_M, cw.altitude)
            if not self.remote_exterior_sensor.is_disabled:
                temp = self.remote_exterior_sensor.get_temperature()
                assert temp
                self._settings.set(
                    LAST_TEMP_C_OUTSIDE,
                    temp.m_as(waqd.unit_reg().degC),
                )
        except Exception as e:
            self._logger.debug("ComponentRegistry: Error while writing last values: " + str(e))

    def watch_all(self):
        """Check all components and thus initialize them"""
        # filter for headless mode
        comps_non_headless = []
        comps = [
            self.weather_info,
            self.auto_updater,
            self.temp_sensor,
            self.humidity_sensor,
            self.tvoc_sensor,
            self.pressure_sensor,
            self.co2_sensor,
            self.motion_detection_sensor,
            self.website_websocket_connection,
        ]
        if not waqd_station.HEADLESS_MODE:
            comps_non_headless = [
                self.event_handler,
                self.display,
                self.tts,
                self.sound,
                self.energy_saver,
            ]
        return comps, comps_non_headless

    # Local only component accessors

    @property
    def display(self) -> Display:
        """Access for Display singleton"""

        return self._create_component_instance(
            Display,
            (
                self._settings.get_string(DISPLAY_TYPE),
                self._settings.get_int(BRIGHTNESS),
                self._settings.get_int(WAVESHARE_DISP_BRIGHTNESS_PIN),
            ),
        )

    @property
    def event_handler(self) -> EventHandler:
        """Access for Greeter singleton"""

        return self._create_component_instance(
            EventHandler,
            (
                self,
                self._settings.get(LANG),
                self._settings.get(NIGHT_MODE_END),
                self._settings.get(EVENTS_ENABLED),
            ),
        )

    @property
    def tts(self) -> TextToSpeach:
        """Access for TTS singleton"""
        return self._create_component_instance(TextToSpeach, (self, self._settings.get(LANG)))

    @property
    def sound(self) -> SoundInterface:
        """Access for Sound singleton"""
        sound_impl = SoundVLC
        if platform.system() == "Linux":
            sound_impl = SoundVLC
        return self._create_component_instance(
            sound_impl, [self, self._settings.get(SOUND_ENABLED)]
        )

    @property
    def energy_saver(self) -> "ESaver":
        """Access for ESaver singleton"""

        return self._create_component_instance(ESaver, (self, self._settings))

    # @property
    # def llm(self):
    #     from waqd.components.llm import LLM
    #     return self._create_component_instance(LLM, [self])

    # Local and remote components

    @property
    def weather_info(self) -> "WeatherProvider":
        """Access for OnlineWeather singleton"""
        return self._create_component_instance(
            OpenMeteo,
            (
                self._settings.get_float(LOCATION_LONGITUDE),
                self._settings.get_float(LOCATION_LATITUDE),
            ),
        )

    # non-disablable components

    @property
    def auto_updater(self) -> "OnlineUpdater":
        """Access for OnlineUpdater singleton"""

        return self._create_component_instance(
            OnlineUpdater,
            (self, self._settings),
        )

    @property
    def website_websocket_connection(self) -> "WAQDDeviceClient":
        """Access for WAQDDeviceClient singleton"""

        return self._create_component_instance(
            WAQDDeviceClient,
            (
                self,
                self._settings.get_string(USER_API_KEY),
                self._settings.get_string(MAC_ADDRESS),
            ),
        )

    # sensors

    @property
    def temp_sensor(self) -> "TempSensor":
        """Access for temperature sensor"""

        sensor = self._get_sensor(TempSensor)
        if not sensor:
            if remote_url := self._settings.get_string(REMOTE_MODE_URL):
                sensor = self._create_component_instance(
                    WAQDRemoteStation,
                    [
                        self,
                        self._settings.get(LOG_SENSOR_DATA),
                        remote_url,
                        self._settings.get_string(REMOTE_API_KEY),
                    ],
                )
            elif self._settings.get(BME_280_ENABLED):
                sensor = self._create_component_instance(BME280, (self, self._settings))
            elif self._settings.get(BMP_280_ENABLED):
                sensor = self._create_component_instance(BMP280, (self, self._settings))
            elif (dht22_pin := self._settings.get(DHT_22_PIN)) != DHT_22_DISABLED:
                sensor = self._create_component_instance(
                    DHT22, [dht22_pin, self, self._settings]
                )
            else:  # create a default instance that is disabled, so the watchdog
                # won't try to instantiate a new one over and over
                sensor = self._create_component_instance(TempSensor, (False, 1, False))
            self._sensors.update({TempSensor.__name__: sensor})
            sensor.select_for_temp_logging()
        return sensor

    @property
    def humidity_sensor(self) -> "HumiditySensor":
        """Access for humidity sensor"""

        sensor = self._get_sensor(HumiditySensor)
        if not sensor:
            if remote_url := self._settings.get_string(REMOTE_MODE_URL):
                sensor = self._create_component_instance(
                    WAQDRemoteStation,
                    (
                        self,
                        self._settings.get(LOG_SENSOR_DATA),
                        remote_url,
                        self._settings.get_string(REMOTE_API_KEY),
                    ),
                )
            elif (dht22_pin := self._settings.get(DHT_22_PIN)) != DHT_22_DISABLED:
                sensor = self._create_component_instance(
                    DHT22, [dht22_pin, self, self._settings]
                )
            elif self._settings.get(BME_280_ENABLED):
                sensor = self._create_component_instance(BME280, (self, self._settings))
            else:  # create a default instance that is disabled
                sensor = self._create_component_instance(HumiditySensor, [False, 1, False])
            self._sensors.update({HumiditySensor.__name__: sensor})
            sensor.select_for_hum_logging()
        return sensor

    @property
    def pressure_sensor(self) -> "BarometricSensor":
        """Access for pressure sensor"""

        sensor = self._get_sensor(BarometricSensor)
        if not sensor:
            if remote_url := self._settings.get_string(REMOTE_MODE_URL):
                sensor = self._create_component_instance(
                    WAQDRemoteStation,
                    (
                        self,
                        self._settings.get(LOG_SENSOR_DATA),
                        remote_url,
                        self._settings.get_string(REMOTE_API_KEY),
                    ),
                )
            elif self._settings.get(BME_280_ENABLED):
                sensor = self._create_component_instance(BME280, (self, self._settings))
            elif self._settings.get(BMP_280_ENABLED):
                sensor = self._create_component_instance(BMP280, (self, self._settings))
            else:  # create a default instance that is disabled
                sensor = self._create_component_instance(BarometricSensor, [False, 1, False])
            self._sensors.update({BarometricSensor.__name__: sensor})
            sensor.select_for_pres_logging()
        return sensor

    @property
    def co2_sensor(self) -> "CO2Sensor":
        """Access for air_quality_sensor"""

        sensor = self._get_sensor(CO2Sensor)
        if not sensor:
            # MH_Z19 is prioritized, if both are available
            if remote_url := self._settings.get_string(REMOTE_MODE_URL):
                sensor = self._create_component_instance(
                    WAQDRemoteStation,
                    (
                        self,
                        self._settings.get(LOG_SENSOR_DATA),
                        remote_url,
                        self._settings.get_string(REMOTE_API_KEY),
                    ),
                )
            elif self._settings.get(MH_Z19_ENABLED):
                sensor = self._create_component_instance(MH_Z19, (self._settings,))
            elif self._settings.get(CCS811_ENABLED):
                sensor = self._create_component_instance(CCS811, (self, self._settings))
            else:  # create a default instance that is disabled
                sensor = self._create_component_instance(CO2Sensor, (False, 1, False))
            self._sensors.update({CO2Sensor.__name__: sensor})
            sensor.select_for_co2_logging()
        return sensor

    @property
    def tvoc_sensor(self) -> "TvocSensor":
        """Access for air_quality_sensor"""

        sensor = self._get_sensor(TvocSensor)
        if not sensor:
            if self._settings.get(CCS811_ENABLED):
                sensor = self._create_component_instance(CCS811, (self, self._settings))
            else:  # create a default instance that is disabled
                sensor = self._create_component_instance(TvocSensor, (False, 1, False))
            self._sensors.update({TvocSensor.__name__: sensor})
            sensor.select_for_tvoc_logging()
        return sensor

    @property
    def dust_sensor(self) -> "DustSensor":
        """Access for dust sensor"""

        sensor = self._get_sensor(DustSensor)
        if not sensor:
            # if self._settings.get(GP2Y1010AU0F_ENABLED):
            #     sensor = self.create_component_instance(GP2Y1010AU0F, [self, self._settings])
            # else:  # create a default instance that is disabled
            sensor = self._create_component_instance(DustSensor, (False, 1, False))
            self._sensors.update({DustSensor.__name__: sensor})
            sensor.select_for_dust_logging()
        return sensor

    @property
    def light_sensor(self) -> "LightSensor":
        """Access for light sensor"""

        sensor = self._get_sensor(LightSensor)
        if not sensor:
            # if self._settings.get(CGY302_ENABLED):
            #     sensor = self.create_component_instance(GY302, [self, self._settings])
            # else:  # create a default instance that is disabled
            sensor = self._create_component_instance(LightSensor, (False, 1, False))
            self._sensors.update({LightSensor.__name__: sensor})
            sensor.select_for_light_logging()
        return sensor

    @property
    def motion_detection_sensor(self) -> "SR501":
        """Access for motion_detection_sensor singleton"""

        sensor = self._get_sensor(SR501)
        if not sensor:
            pin = self._settings.get_int(MOTION_SENSOR_PIN)
            if self._settings.get(MOTION_SENSOR_ENABLED) and pin > 0:
                sensor = self._create_component_instance(SR501, (pin,))
            else:  # create a default instance that is disabled
                sensor = self._create_component_instance(SR501, (0,))
            self._sensors.update({SR501.__name__: sensor})
        return sensor

    @property
    def remote_exterior_sensor(self) -> "WAQDRemoteSensor":
        """Access for remote_exterior_sensor singleton"""
        from waqd.components.sensor_base import WAQDRemoteSensor

        sensor = self._get_sensor(WAQDRemoteSensor)
        if not sensor:
            sensor = self._create_component_instance(
                WAQDRemoteSensor, (SENSOR_EXTERIOR_TYPE, self._settings.get(LOG_SENSOR_DATA))
            )
            # TODO check features - diff ext and int
            sensor.select_for_hum_logging()
            sensor.select_for_temp_logging()
            self._sensors.update({WAQDRemoteSensor.__name__: sensor})
        return sensor

    @property
    def remote_interior_sensor(self) -> "WAQDRemoteSensor":
        """Access for remote_interior_sensor singleton"""
        from waqd.components.sensor_base import WAQDRemoteSensor

        sensor = self._get_sensor(WAQDRemoteSensor)
        if not sensor:
            sensor = self._create_component_instance(
                WAQDRemoteSensor, (SENSOR_INTERIOR_TYPE, self._settings.get(LOG_SENSOR_DATA))
            )
            sensor.select_for_hum_logging()
            sensor.select_for_temp_logging()
            self._sensors.update({WAQDRemoteSensor.__name__: sensor})
        return sensor
