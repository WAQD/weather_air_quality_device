"""
This module contains all high abstraction classes of sensors, which internally
periodically call get a value (or use callbacks).
"""

import datetime
from statistics import mean
from typing import TYPE_CHECKING, Optional

import requests

from waqd import LOCAL_TIMEZONE
from waqd import unit_reg
from waqd.base.component import Component, CyclicComponent
from waqd.base.component_reg import ComponentRegistry
from waqd.base.db_logger import InfluxSensorLogger
from waqd.base.file_logger import Logger, SensorFileLogger
from waqd.base.network import Network
from waqd.base.system import RuntimeSystem
from waqd.web.api.sensor.v1 import SensorApi_v1

if TYPE_CHECKING:
    from pint.facets.plain import PlainQuantity as Quantity

SENSOR_INTERIOR_TYPE = "interior"
SENSOR_EXTERIOR_TYPE = "exterior"
DEFAULT_MAX_MEASURE_POINTS = 5
DEFAULT_INVALIDATION_TIME_S = 60

if RuntimeSystem().is_target_system:
    SensorValueLogger = InfluxSensorLogger
else:
    SensorValueLogger = SensorFileLogger


class SensorComponent(Component):
    def __init__(self, enabled=True):
        super().__init__(enabled=enabled)
        self._readings_stabilized = False

    @property
    def readings_stabilized(self) -> bool:
        """Returns true, if sensor is warmed up and readings are considered valid."""
        return self._readings_stabilized

    @property
    def is_disabled(self) -> bool:
        return self._disabled

    def get_value_with_status(self, impl: "SensorImpl"):
        if self._disabled:
            return None
        value = impl.get_value()
        if value is None:
            self._disabled = True
        self._disabled = False
        return value


class SensorImpl:
    """Class for any sensor type to store measurements with a moving average.
    Logs to file/db, if "log_to_file" is activated.
    To be used with pimpl pattern and not as a base class!
    """

    LOGGING_INTERVAL = datetime.timedelta(minutes=1)
    MAX_TIMES_DELTA_VIOLATED = 1

    def __init__(
        self,
        logging_enabled: bool,
        log_location_type: str,
        log_measure_type: str,
        min_value: float,
        max_value: float,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        default_value=0,
        invalidation_time_s=30,
        max_delta=0,
        rounding_precision=2,
        rounding_base=1.0,
    ):
        # logging
        self.log_values = False  # Select this instance for global for logging
        # only check at init - options will reset this flag, with the exception of non-resettable sensors
        self._logging_enabled = logging_enabled
        self._log_measure_type = log_measure_type  # like temp or hum
        self._log_location_type = log_location_type  # like interior or exterior
        # value validation and rounding
        self._rounding_base = rounding_base
        self._rounding_prec = rounding_precision
        self._min_value = min_value  # for validation: outside this range invalid
        self._max_value = max_value  # same as min_value
        # maximum deviation for previous value - to detect errors (0 means disabled)
        self._max_delta = max_delta
        self._n_delta_violation = (
            0  # track violations - after MAX_TIMES_DELTA_VIOLATED times still take it
        )
        self._first_value_written = False
        # value storage
        self._values_capacity = max_measure_points  # number of elements of the moving average
        self._values = []
        # After invalidation_time_s has passed, the sensor value will be considered out of date and return None for value
        # Does not make sense for motion sensors and such.
        self._last_value_rcv_time = datetime.datetime.now()
        self._value_invalidation_time_s = invalidation_time_s
        self._last_logging_time = datetime.datetime.now()

        # even if logging is disabled now we should attempt to restore the last recorded value
        # TODO does not work because of time limit - need find last value
        # use file logger when shuttings down and read back here
        if logging_enabled:
            # only enabled sensor returns values
            log_values = SensorValueLogger.get_sensor_values(
                self._log_location_type, self._log_measure_type
            )
            if log_values:
                if len(log_values[0]) < 2:
                    Logger().warning(
                        f"Cant initialize {log_measure_type} sensor from log. Invalid log format."
                    )
                else:
                    try:
                        last_date = log_values[0][0]
                    except Exception:
                        return
                    if (last_date - datetime.datetime.now(LOCAL_TIMEZONE)) < datetime.timedelta(
                        hours=3
                    ):
                        self._values.append(log_values[0][1])
            else:
                self._values.append(default_value)
        else:
            self._values.append(default_value)

    def stop(self):
        pass

    def get_value(self) -> Optional[float]:
        """Return measurement value."""
        # invalidation guard
        if datetime.datetime.now() - self._last_value_rcv_time > datetime.timedelta(
            seconds=self._value_invalidation_time_s
        ):
            Logger().debug(
                f"Invalidated value of {self.__class__.__name__} {self._log_measure_type}"
            )
            return None
        if self._values_capacity == 1:
            return self._values[0]
        else:
            return mean(self._values)

    @staticmethod
    def round(value: float, prec=2, base=0.05):
        return round(base * round(value / base), prec)

    def set_value(self, value: Optional[float]) -> bool:
        """Generic method to write values into the measurement list and manage its length"""
        # out of bounds check
        Logger().debug(
            "%s: %s Attempting to write %f",
            self.__class__.__name__,
            self._log_measure_type,
            value,
        )
        if value is None:
            return False
        value = self.round(value, self._rounding_prec, self._rounding_base)
        if not self._min_value <= value <= self._max_value:
            Logger().warning(
                "%s: %s out of bounds %s",
                self.__class__.__name__,
                self._log_measure_type,
                value,
            )
            return False
        # max delta check - only check after first value has truly been written

        if self._max_delta and self._first_value_written:
            if current_value := self._values[-1]:
                current_delta = abs(value - current_value)
                if current_delta >= self._max_delta:
                    if self._n_delta_violation < self.MAX_TIMES_DELTA_VIOLATED:
                        self._n_delta_violation += 1
                        Logger().warning(
                            "%s: %s max delta reached %s",
                            self.__class__.__name__,
                            self._log_measure_type,
                            current_delta,
                        )
                        return False
                    else:
                        Logger().warning(
                            "%s: %s taking value after max delta reached.",
                            self.__class__.__name__,
                            self._log_measure_type,
                        )
                        self._n_delta_violation = 0
        self._values.append(value)
        self._last_value_rcv_time = datetime.datetime.now()
        self._first_value_written = True

        if len(self._values) > self._values_capacity:
            self._values.pop(0)
        # log only at full measurement window - slower logging
        if self._logging_enabled and self.log_values:
            if datetime.datetime.now() - self._last_logging_time <= self.LOGGING_INTERVAL:
                return True
            # log the mean average of the values
            SensorValueLogger.set_value(
                self._log_location_type, self._log_measure_type, self.get_value()
            )
            self._last_logging_time = datetime.datetime.now()
        return True


class TempSensor(SensorComponent):
    """Base class for all temperature sensors"""

    __MIN_VALUE = -30
    __MAX_VALUE = 60
    __DEFAULT_VALUE = 22
    __MAX_DELTA = 3

    def __init__(
        self,
        logging_enabled: bool,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        enabled=True,
        log_location_type=SENSOR_INTERIOR_TYPE,
        log_measure_type="temp_degC",
        invalidation_time_s=DEFAULT_INVALIDATION_TIME_S,
    ):
        """is_disabled is for the case, when no sensor can be instantiated"""
        SensorComponent.__init__(self, enabled=enabled)
        self._temp_impl = SensorImpl(
            logging_enabled,
            log_location_type,
            log_measure_type,
            self.__MIN_VALUE,
            self.__MAX_VALUE,
            max_measure_points,
            self.__DEFAULT_VALUE,
            invalidation_time_s,
            self.__MAX_DELTA,
            rounding_base=0.1,
            rounding_precision=1,
        )
        self.get_temperature()  # init unit registry

    def select_for_temp_logging(self):
        self._temp_impl.log_values = True

    def get_temperature(self) -> Optional["Quantity"]:
        """Return temperature in degree Celsius"""
        value = self.get_value_with_status(self._temp_impl)
        if value is not None:
            return unit_reg().Quantity(value, "degC")
        return None

    def _set_temperature(self, value: Optional[float]) -> bool:
        return self._temp_impl.set_value(value)

    def stop(self):
        self._temp_impl.stop()
        super().stop()


class BarometricSensor(SensorComponent):
    """Base class for all barometric sensors"""

    __MIN_VALUE = 800
    __MAX_VALUE = 2000
    __DEFAULT_VALUE = 1000
    __MAX_DELTA = 3

    def __init__(
        self,
        logging_enabled: bool,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        enabled=True,
        log_location_type=SENSOR_INTERIOR_TYPE,
        log_measure_type="pressure_hPa",
        invalidation_time_s=DEFAULT_INVALIDATION_TIME_S,
    ):
        SensorComponent.__init__(self, enabled=enabled)
        self._pres_impl = SensorImpl(
            logging_enabled,
            log_location_type,
            log_measure_type,
            self.__MIN_VALUE,
            self.__MAX_VALUE,
            max_measure_points,
            self.__DEFAULT_VALUE,
            invalidation_time_s,
            max_delta=self.__MAX_DELTA,
            rounding_precision=1,
        )

    def select_for_pres_logging(self):
        self._pres_impl.log_values = True

    def get_pressure(self) -> Optional["Quantity"]:
        """Return the pressure in hPa"""
        value = self.get_value_with_status(self._pres_impl)
        if value is not None:
            return unit_reg().Quantity(value, "hPa")
        return None

    def _set_pressure(self, value: Optional[float]):
        self._pres_impl.set_value(value)

    def _convert_abs_pres_to_asl(self, pressure: float, height_asl: float, temp_outdoor: float):
        """Converts raw absolute readings to above sea level relative readings, which are used in weather forecasts."""
        return pressure * pow(
            1 - (0.0065 * height_asl / (temp_outdoor + (0.0065 * height_asl) + 273.15)), -5.257
        )

    def stop(self):
        self._pres_impl.stop()
        super().stop()


class HumiditySensor(SensorComponent):
    """Base class for all humidity sensors"""

    __MIN_VALUE = 10
    __MAX_VALUE = 100
    __DEFAULT_VALUE = 50
    __MAX_DELTA = 10

    def __init__(
        self,
        logging_enabled: bool,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        enabled=True,
        log_location_type=SENSOR_INTERIOR_TYPE,
        log_measure_type="humidity_%",
        invalidation_time_s=DEFAULT_INVALIDATION_TIME_S,
    ):
        SensorComponent.__init__(self, enabled=enabled)
        self._hum_impl = SensorImpl(
            logging_enabled,
            log_location_type,
            log_measure_type,
            self.__MIN_VALUE,
            self.__MAX_VALUE,
            max_measure_points,
            self.__DEFAULT_VALUE,
            invalidation_time_s,
            max_delta=self.__MAX_DELTA,
            rounding_precision=1,
        )

    def select_for_hum_logging(self):
        self._hum_impl.log_values = True

    def get_humidity(self) -> Optional["Quantity"]:
        """Return the humidity in %"""
        value = self.get_value_with_status(self._hum_impl)
        if value is not None:
            return unit_reg().Quantity(value, "percent")
        return None

    def _set_humidity(self, value: Optional[float]):
        self._hum_impl.set_value(value)

    def stop(self):
        self._hum_impl.stop()
        super().stop()


class TvocSensor(SensorComponent):
    """Base class for all TVOC sensors"""

    __MIN_VALUE = 0
    __MAX_VALUE = 500
    __DEFAULT_VALUE = 0
    __MAX_DELTA = 100

    def __init__(
        self,
        logging_enabled: bool,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        enabled=True,
        log_location_type=SENSOR_INTERIOR_TYPE,
        log_measure_type="TVOC",
        invalidation_time_s=DEFAULT_INVALIDATION_TIME_S,
    ):
        SensorComponent.__init__(self, enabled=enabled)
        self._tvoc_impl = SensorImpl(
            logging_enabled,
            log_location_type,
            log_measure_type,
            self.__MIN_VALUE,
            self.__MAX_VALUE,
            max_measure_points,
            self.__DEFAULT_VALUE,
            invalidation_time_s,
            max_delta=self.__MAX_DELTA,
            rounding_precision=0,
            rounding_base=5,
        )

    def select_for_tvoc_logging(self):
        self._tvoc_impl.log_values = True

    def get_tvoc(self) -> Optional["Quantity"]:
        """Returns TVOC in ppb"""
        value = self.get_value_with_status(self._tvoc_impl)
        if value is not None:
            return unit_reg().Quantity(value, "ppb")
        return None

    def _set_tvoc(self, value: Optional[float]):
        self._tvoc_impl.set_value(value)

    def stop(self):
        self._tvoc_impl.stop()
        super().stop()


class CO2Sensor(SensorComponent):
    """Base class for all CO2 sensors"""

    __MIN_VALUE = 400
    __MAX_VALUE = 5000
    __DEFAULT_VALUE = 450
    __MAX_DELTA = 50

    def __init__(
        self,
        logging_enabled: bool,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        enabled=True,
        log_location_type=SENSOR_INTERIOR_TYPE,
        log_measure_type="CO2_ppm",
        invalidation_time_s=DEFAULT_INVALIDATION_TIME_S,
    ):
        SensorComponent.__init__(self, enabled=enabled)
        self._co2_impl = SensorImpl(
            logging_enabled,
            log_location_type,
            log_measure_type,
            self.__MIN_VALUE,
            self.__MAX_VALUE,
            max_measure_points,
            self.__DEFAULT_VALUE,
            invalidation_time_s,
            max_delta=self.__MAX_DELTA,
            rounding_precision=1,
            rounding_base=5,
        )

    def select_for_co2_logging(self):
        self._co2_impl.log_values = True

    def get_co2(self) -> Optional["Quantity"]:
        """Returns equivalent CO2 in ppm"""
        value = self.get_value_with_status(self._co2_impl)
        if value is not None:
            return unit_reg().Quantity(value, "ppm")
        return None

    def _set_co2(self, value: Optional[float]):
        self._co2_impl.set_value(value)

    def stop(self):
        self._co2_impl.stop()
        super().stop()


class DustSensor(SensorComponent):
    """Base class for all dust sensors"""

    __MIN_VALUE = 0
    __MAX_VALUE = 1000
    __DEFAULT_VALUE = 100
    __MAX_DELTA = 100

    def __init__(
        self,
        logging_enabled: bool,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        enabled=True,
        log_location_type=SENSOR_INTERIOR_TYPE,
        log_measure_type="dust_ug_per_m3",
        invalidation_time_s=DEFAULT_INVALIDATION_TIME_S,
    ):
        SensorComponent.__init__(self, enabled=enabled)
        self._dust_impl = SensorImpl(
            logging_enabled,
            log_location_type,
            log_measure_type,
            self.__MIN_VALUE,
            self.__MAX_VALUE,
            max_measure_points,
            self.__DEFAULT_VALUE,
            invalidation_time_s,
            max_delta=self.__MAX_DELTA,
            rounding_precision=0,
        )

    def select_for_dust_logging(self):
        self._dust_impl.log_values = True

    def get_dust(self) -> Optional["Quantity"]:
        """Returns dust in ug/m^3"""
        value = self.get_value_with_status(self._dust_impl)
        if value is not None:
            return unit_reg().Quantity(value, "ug / m ** 3")
        return None

    def _set_dust(self, value: Optional[float]):
        self._dust_impl.set_value(value)

    def stop(self):
        self._dust_impl.stop()
        super().stop()


class LightSensor(SensorComponent):
    """Base class for all light sensors"""

    __MIN_VALUE = 0  # dark
    __MAX_VALUE = 100000  # direct sunlight
    __DEFAULT_VALUE = 10000
    __MAX_DELTA = 0  # infinity

    def __init__(
        self,
        logging_enabled,
        max_measure_points=DEFAULT_MAX_MEASURE_POINTS,
        enabled=True,
        log_location_type=SENSOR_INTERIOR_TYPE,
        log_measure_type="light_lux",
        invalidation_time_s=15,
    ):
        SensorComponent.__init__(self, enabled=enabled)
        self._light_impl = SensorImpl(
            logging_enabled,
            log_location_type,
            log_measure_type,
            self.__MIN_VALUE,
            self.__MAX_VALUE,
            max_measure_points,
            self.__DEFAULT_VALUE,
            invalidation_time_s,
            max_delta=self.__MAX_DELTA,
            rounding_precision=1,
        )

    def select_for_light_logging(self):
        self._light_impl.log_values = True

    def get_light(self) -> Optional["Quantity"]:
        """Returns light in lux"""
        value = self.get_value_with_status(self._light_impl)
        if value is not None:
            return unit_reg().Quantity(value, "lux")
        return None

    def _set_light(self, value: Optional[float]):
        self._light_impl.set_value(value)

    def stop(self):
        self._light_impl.stop()
        super().stop()

class WAQDRemoteSensor(TempSensor, HumiditySensor, BarometricSensor, CO2Sensor):
    """Remote sensor via WAQD HTTP service"""

    MEASURE_POINTS = 3

    def __init__(self, mode=SENSOR_EXTERIOR_TYPE, log_sensor_data=False):
        TempSensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=mode,
            invalidation_time_s=60,
        )
        HumiditySensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=mode,
            invalidation_time_s=60,
        )
        BarometricSensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=mode,
            invalidation_time_s=60,
        )
        CO2Sensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=mode,
            invalidation_time_s=60,
        )
        self._disabled = True  # don't know if connected at startup

    def read_callback(self, temperature=None, humidity=None, pressure=None, co2=None):
        """ """
        self._disabled = False

        self._set_temperature(temperature)
        self._set_humidity(humidity)
        self._set_pressure(pressure)
        self._set_co2(co2)
        self._logger.debug(
            "WAQDExtTempSensor: Temp=%0.1f*C Humidity=%0.1f%% Pressure=%s hPa CO2=%s ppm",
            temperature,
            humidity,
            pressure,
            co2,
        )


class WAQDRemoteStation(
    TempSensor, HumiditySensor, BarometricSensor, CO2Sensor, CyclicComponent
):
    MEASURE_POINTS = 1
    INIT_WAIT_TIME = 2
    UPDATE_TIME = 10

    def __init__(
        self, components: ComponentRegistry, log_sensor_data: bool, url: str, api_key: str
    ):
        self._url = url
        self._api_key = api_key

        TempSensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=SENSOR_INTERIOR_TYPE,
            invalidation_time_s=self.UPDATE_TIME * 6,
        )
        HumiditySensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=SENSOR_INTERIOR_TYPE,
            invalidation_time_s=self.UPDATE_TIME * 6,
        )
        BarometricSensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=SENSOR_INTERIOR_TYPE,
            invalidation_time_s=self.UPDATE_TIME * 6,
        )
        CO2Sensor.__init__(
            self,
            log_sensor_data,
            self.MEASURE_POINTS,
            log_location_type=SENSOR_INTERIOR_TYPE,
            invalidation_time_s=self.UPDATE_TIME * 6,
        )
        CyclicComponent.__init__(self, components, enabled=log_sensor_data)
        self._start_update_loop(self._read_sensor, self._read_sensor)

        self._readings_stabilized = (
            True  # init with stabilized values, we know nothing about it
        )

    def _read_sensor(self):
        Network().wait_for_network()
        url = self._url + "/api/sensor/v1/interior"
        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": "Bearer " + self._api_key,
                },
                timeout=5,
            )
        except Exception as e:
            Logger().warning(f"Cannot reach {url}" + str(e))
            return
        if not response.ok:
            Logger().warning(f"Cannot reach {url}: {response.text}")
            return ()
        content: SensorApi_v1 = SensorApi_v1(**response.json())
        val = content.temp
        if val and val not in ["None", "N/A"]:
            self._set_temperature(float(val))
        val = content.hum
        if val and val not in ["None", "N/A"]:
            self._set_humidity(float(val))
        val = content.baro
        if val and val not in ["None", "N/A"]:
            self._set_pressure(int(val))
        val = content.co2
        if val and val not in ["None", "N/A"]:
            self._set_co2(float(val))
