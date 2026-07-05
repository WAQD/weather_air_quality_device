"""
This module contains all high abstraction classes of sensors, which internally
periodically call get a value (or use callbacks).
"""

import datetime
import os
import sys
import threading
import time
from ast import literal_eval
from subprocess import check_output
from typing import TYPE_CHECKING

import board
import RPi.GPIO
from nmcli import NetworkConnectivity

from waqd import unit_reg
from waqd.base.component import CyclicComponent
from waqd.base.db_logger import InfluxSensorLogger
from waqd.base.file_logger import SensorFileLogger
from waqd.base.network import Network
from waqd.base.system import RuntimeSystem
from waqd.components.sensor_base import (
    BarometricSensor,
    CO2Sensor,
    DustSensor,
    HumiditySensor,
    LightSensor,
    SensorComponent,
    TempSensor,
    TvocSensor,
)
from waqd_station.settings import (
    BMX280_TEMP_OFFSET_C,
    LAST_TEMP_C_OUTSIDE,
    LOCATION_ALTITUDE_M,
    LOG_SENSOR_DATA,
    MH_Z19_VALUE_OFFSET,
    Settings,
)

if TYPE_CHECKING:
    import adafruit_bh1750
    import adafruit_bmp280
    import adafruit_ccs811
    from adafruit_bme280.advanced import Adafruit_BME280_I2C
    from gpiozero import MotionSensor
    from waqd_station.app.component_reg import ComponentRegistry

SENSOR_INTERIOR_TYPE = "interior"
SENSOR_EXTERIOR_TYPE = "exterior"
DEFAULT_MAX_MEASURE_POINTS = 5
DEFAULT_INVALIDATION_TIME_S = 60

if RuntimeSystem().is_target_system:
    SensorValueLogger = InfluxSensorLogger
else:
    SensorValueLogger = SensorFileLogger


class DHT22(TempSensor, HumiditySensor, CyclicComponent):
    """
    Implements access to the DHT22 temperature/humidity sensor.
    """

    UPDATE_TIME = 5  # in seconds
    MEASURE_POINTS = 2

    def __init__(self, pin: int, components: "ComponentRegistry", settings: Settings):
        log_values = bool(settings.get(LOG_SENSOR_DATA))
        TempSensor.__init__(self, log_values, self.MEASURE_POINTS)
        HumiditySensor.__init__(self, log_values, self.MEASURE_POINTS)
        CyclicComponent.__init__(self, components, enabled=bool(pin))
        self._comps: "ComponentRegistry"
        self._pin = pin
        self._sensor_driver = None
        self._error_num = 0
        if self._disabled:
            self._logger.error("DHT22: No pin, disabled")
            return
        self._start_update_loop(self._init_sensor, self._read_sensor)

    def _init_sensor(self):
        """
        Initialize sensor (simply save the module), no complicated init needed.
        """
        from adafruit_dht import DHT22 as DHT22_drv

        # driver uses pulseio - only one process can be open
        self._kill_libgpiod()
        self._sensor_driver = DHT22_drv(self._pin)

    def _read_sensor(self):
        """
        Reads the actual values in the moving average list.
        Ignores comm. errors, but does simple value validity checks.
        """
        humidity = 0
        temperature = 0
        if not self._sensor_driver:
            self._disabled = True
            return

        temperature = None
        humidity = None
        while not temperature and not humidity:
            try:
                humidity = self._sensor_driver.humidity
                temperature = self._sensor_driver.temperature
            except Exception as error:
                self._error_num += 1
                # errors happen fairly often, keep going
                self._logger.debug("DHT22: Can't read sensor - %s", str(error))
            if self._error_num >= 5:
                self._logger.error("DHT22: Restarting sensor after 5 errors")
                self._comps.stop_component_instance(self)
                return
        self._error_num = 0

        self._set_humidity(humidity)
        valid = self._set_temperature(temperature)
        if not valid:
            self._error_num += 1

        self._logger.debug(
            "DHT22: Temp={0:0.1f}*C  Humidity={1:0.1f}%".format(temperature, humidity)
        )

    def stop(self):  # override Component
        super().stop()
        if self._sensor_driver:
            self._sensor_driver.exit()
            del self._sensor_driver
            self._sensor_driver = None
            self._kill_libgpiod()

    def _kill_libgpiod(self):
        if not self._runtime_system.is_target_system:  # don't check on non target system
            return
        try:
            pids = check_output(["pgrep", "libgpiod_pulsei"]).decode("utf-8")
            for pid in pids.split("\n"):
                os.system("kill " + str(pid))
        except Exception as error:  # works on RPi3 pulsi does not
            self._logger.warning(
                "DHT22: Exception while checking running pulseio process: %s", str(error)
            )


class BMP280(TempSensor, BarometricSensor, CyclicComponent):
    """
    Implements access to the BMP280 temperature/pressure sensor.
    """

    UPDATE_TIME = 5  # in seconds
    MEASURE_POINTS = 2

    def __init__(self, components: "ComponentRegistry", settings: Settings):
        log_values = bool(settings.get(LOG_SENSOR_DATA))
        self._comps: "ComponentRegistry"
        TempSensor.__init__(self, log_values, self.MEASURE_POINTS)
        BarometricSensor.__init__(self, log_values, self.MEASURE_POINTS)
        CyclicComponent.__init__(self, components, settings)

        self._sensor_driver: "adafruit_bmp280.Adafruit_BMP280_I2C"
        self._start_update_loop(self._init_sensor, self._read_sensor)

    def _init_sensor(self):
        """
        Initialize sensor (simply save the module), no complicated init needed.
        """
        # use the old Adafruit driver, the new one is more unstable
        import adafruit_bmp280

        i2c = board.I2C()  # uses board.SCL and board.SDA
        self._sensor_driver = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)

    def _read_sensor(self):
        """
        Reads the actual values in the moving average list.
        Ignores comm. errors, but does simple value validity checks.
        """
        temperature = 0
        pressure = 0
        try:
            temperature = self._sensor_driver.temperature
            pressure = self._sensor_driver.pressure
        except Exception as error:
            # errors happen fairly often, keep going
            self._logger.error("BMP280: Can't read sensor - %s", str(error))
            return
        altitude = self._settings.get_float(LOCATION_ALTITUDE_M)
        temp_outside = self._settings.get_float(LAST_TEMP_C_OUTSIDE)
        weather = self._comps.weather_info.get_current_weather()
        if weather:
            altitude = weather.altitude
            temp_outside = weather.temp

        self._set_pressure(self._convert_abs_pres_to_asl(pressure, altitude, temp_outside))  # type: ignore
        self._set_temperature(temperature)

        self._logger.debug(
            "BMP280: Temp={0:0.1f}*C  Pressure={1}hPa".format(temperature, pressure)
        )


class BME280(TempSensor, BarometricSensor, HumiditySensor, CyclicComponent):
    """
    Implements access to the BME280 temperature/humidity/pressure sensor.
    """

    UPDATE_TIME = 5  # in seconds
    MEASURE_POINTS = 5

    def __init__(self, components: "ComponentRegistry", settings: Settings):
        log_values = bool(settings.get(LOG_SENSOR_DATA))
        self._comps: "ComponentRegistry"
        TempSensor.__init__(self, log_values, self.MEASURE_POINTS)
        BarometricSensor.__init__(self, log_values, self.MEASURE_POINTS)
        HumiditySensor.__init__(self, log_values, self.MEASURE_POINTS)
        CyclicComponent.__init__(self, components, settings)

        self._sensor_driver: "Adafruit_BME280_I2C"
        self._start_update_loop(self._init_sensor, self._read_sensor)

    def _init_sensor(self):
        """
        Initialize sensor (simply save the module), no complicated init needed.
        """
        from adafruit_bme280.advanced import Adafruit_BME280_I2C

        i2c = board.I2C()  # uses board.SCL and board.SDA
        self._sensor_driver = Adafruit_BME280_I2C(i2c, address=0x76)

    def _read_sensor(self):
        """
        Reads the actual values in the moving average list.
        Ignores comm. errors, but does simple value validity checks.
        """
        temperature = 0
        pressure = 0
        humidity = 0
        try:
            temperature = self._sensor_driver.temperature + self._settings.get_float(BMX280_TEMP_OFFSET_C)
            pressure = self._sensor_driver.pressure
            humidity = self._sensor_driver.humidity
        except Exception as error:
            # errors happen fairly often, keep going
            self._logger.error("BME280: Can't read sensor - %s", str(error))
            return

        # change this to match the location's pressure (hPa) at sea level
        altitude = self._settings.get_float(LOCATION_ALTITUDE_M)
        temp_outside = self._settings.get_float(LAST_TEMP_C_OUTSIDE)
        if Network().get_connectivity() == NetworkConnectivity.FULL:
            weather = self._comps.weather_info.get_current_weather()
            if weather:
                altitude = weather.altitude
                temp_outside = weather.temp

        self._set_pressure(self._convert_abs_pres_to_asl(pressure, altitude, temp_outside))
        self._set_temperature(temperature)
        self._set_humidity(humidity)

        self._logger.debug(
            "BME280: Temp={0:0.1f}*C  Pressure={1}hPa Humidity={2:0.1f}%".format(
                temperature, pressure, humidity
            )
        )


class MH_Z19(CO2Sensor, CyclicComponent):  # pylint: disable=invalid-name
    """
    Implements access to the MH-Z19 CO2 sensor.
    Return the values as a moving average of the last points.
    Does not measure temperature, because it is very imprecise.
    """

    UPDATE_TIME = 3  # in seconds
    MEASURE_POINTS = 5
    STABILIZE_TIME_MINUTES = 1  # in minutes

    def __init__(self, settings: Settings):
        log_values = bool(settings.get(LOG_SENSOR_DATA))
        CO2Sensor.__init__(self, log_values, self.MEASURE_POINTS)
        CyclicComponent.__init__(self)
        self._offset = settings.get_int(MH_Z19_VALUE_OFFSET)
        self._start_time = datetime.datetime.now()
        self._readings_stabilized = False
        self._error_num = 0
        self._start_update_loop(self._init_sensor, self._read_sensor)

    def _init_sensor(self):
        # Switched to sudo + cli of the python module, because I found no reliable way
        # to automate the permission settings for the serial interface,
        # because of a bug? it resets after calling the python serial module.
        if self._runtime_system.is_target_system:
            try:
                os.system(f"sudo {sys.executable} -m mh_z19 --detection_range_5000")
            except Exception:
                os.system(f"sudo {sys.executable} -m mh_z19 --detection_range_2000")
            # disable auto calibration -> it will never read true 400ppm...
            os.system(f"sudo {sys.executable} -m mh_z19 --abc_off")

    def _read_sensor(self):
        co2 = 0
        output = ""
        self._error_num = 0
        while not co2 and self._error_num < 10:
            try:
                # Parse back from cli
                if self._runtime_system.is_target_system:
                    cmd = ["sudo", sys.executable, "-m", "mh_z19"]
                else:  # for local tests
                    cmd = [sys.executable, "-m", "mh_z19"]
                output = check_output(cmd).decode("utf-8")
                output.strip()
                if not output or "co2" not in output.lower():
                    self._error_num += 1
                else:
                    co2 = int(literal_eval(output).get("co2", ""))
            except Exception as error:
                # errors happen fairly often, keep going
                self._logger.error(
                    f"MH-Z19: Can't read sensor - {str(error)} Output: {output}",
                )
                return
        if not co2:
            self._logger.error("MH-Z19: Error in reading sensor after 10 tries")
            return
        self._set_co2(co2 + self._offset)

        # eval stabilizer time
        stab_time = datetime.timedelta(minutes=self.STABILIZE_TIME_MINUTES)
        if datetime.datetime.now() > self._start_time + stab_time:
            self._readings_stabilized = True

        # log if value is readable
        self._logger.debug("MH-Z19: CO2={0:0.1f}ppm".format(co2))

    def zero_calibraton(self):
        os.system(f"sudo {sys.executable} -m mh_z19 --zero_point_calibration")


class CCS811(CO2Sensor, TvocSensor, CyclicComponent):  # pylint: disable=invalid-name
    """
    Implements access to the CCS811 CO2/TVOC sensor.
    Return the values as a moving average of the last points.
    """

    UPDATE_TIME = 3  # in seconds
    STABILIZE_TIME_MINUTES = 30  # minutes
    MEASURE_POINTS = 3

    def __init__(self, components: "ComponentRegistry", settings: Settings):
        log_values = bool(settings.get(LOG_SENSOR_DATA))
        CO2Sensor.__init__(self, log_values, self.MEASURE_POINTS)
        TvocSensor.__init__(self, log_values, self.MEASURE_POINTS)
        CyclicComponent.__init__(self, components)
        self._comps: "ComponentRegistry"

        self._start_time = datetime.datetime.now()
        self._reload_forbidden = True
        self._sensor_driver: "adafruit_ccs811.CCS811"
        self._error_num = 0

        self._start_update_loop(self._init_sensor, self._read_sensor)

    def _init_sensor(self):
        """
        Inits driver and tries to communicate.
        Imports the real driver only on target platform.
        """
        import adafruit_ccs811
        import busio  # pylint: disable=import-outside-toplevel

        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self._sensor_driver = adafruit_ccs811.CCS811(i2c)

            # wait for the sensor to be ready - try max 3 times
            i = 0
            while not self._sensor_driver.data_ready and i <= 3:
                i += 1
                time.sleep(1)
        except Exception as error:
            self._logger.error("CCS811: can not be initialized - %s", str(error))
            return

    def _react_on_error(self):
        if self._error_num == 2:
            self._logger.error("CCS811: Error in reading sensor. Resetting ...")
            if self._sensor_driver:
                try:
                    self._sensor_driver.reset()
                except Exception as error:
                    self._logger.error("CCS811: can not be resetted - %s", str(error))
                    self._disabled = True
            else:  # driver failed to start (wiring issues?)
                self._disabled = True
        if self._error_num == 3:
            self._logger.error("CCS811: Error in reading sensor. Restarting...")
            del self._sensor_driver
            self._init_sensor()

    def _set_environmental_values(self):
        """
        If there is a temperature/humidity sensor, it can be
        used to initalize this sensor, so it has more accurate measurements
        """
        temperature = self._comps.temp_sensor.get_temperature()
        humidity = self._comps.humidity_sensor.get_humidity()
        # wait for values to stabilize
        if temperature is None or humidity is None:
            return
        while not 15 < temperature.m_as(unit_reg().degC) < 50:
            time.sleep(2)

        self._sensor_driver.set_environmental_data(int(humidity), float(temperature))

    def _read_sensor(self):
        """
        Cyclic function for reading the actual values into a moving average list.
        Sets environment values from an optional temp/hum sensor.
        Does a soft restart after 2 errors and a hard reset after 3 errors.
        """
        co2 = None
        tvoc = None
        try:
            self._react_on_error()
            if self._sensor_driver.data_ready:
                co2 = self._sensor_driver.eco2
                tvoc = self._sensor_driver.tvoc
                # eval stabilizer time
                stab_time = datetime.timedelta(minutes=self.STABILIZE_TIME_MINUTES)
                if datetime.datetime.now() > self._start_time + stab_time:
                    self._readings_stabilized = True

            else:
                self._error_num += 1
                return

            self._error_num = 0
        except Exception as error:  # there are a miriad of errors...
            self._error_num += 1
            self._logger.error("CCS811: Error in reading sensor - %s", str(error))
            return

        self._set_co2(co2)
        self._set_tvoc(tvoc)

        # log if every value is readable
        self._logger.debug("CCS811: CO2={0:0.1f}ppm TVOC={1:0.1f}".format(co2, tvoc))


class BH1750(LightSensor, CyclicComponent):
    """
    Implements access to the BH1750 light intensity sensor.
    WARNING: PROTOTYPE STATUS!
    """

    UPDATE_TIME = 1  # in seconds

    def __init__(self, settings: Settings):
        MEASURE_POINTS = 2
        log_values = bool(settings.get(LOG_SENSOR_DATA))
        LightSensor.__init__(self, log_values, MEASURE_POINTS)
        CyclicComponent.__init__(self)

        self._sensor_driver: "adafruit_bh1750.BH1750"
        self._start_update_loop(self._init_sensor, self._read_sensor)

    def _init_sensor(self):
        """
        Initialize sensor (simply save the module), no complicated init needed.
        """
        import adafruit_bh1750

        i2c = board.I2C()
        self._sensor_driver = adafruit_bh1750.BH1750(i2c)

    def _read_sensor(self):
        """
        Reads the actual values in the moving average list.
        Ignores comm. errors, but does simple value validity checks.
        """
        light = 0
        try:
            self._sensor_driver.lux
        except Exception as error:
            # errors happen fairly often, keep going
            self._logger.error("GY302: Can't read sensor - %s", str(error))
            return
        self._set_light(light)
        self._logger.debug("GY302: Light={0:0.1f}Lux".format(light))


class GP2Y1010AU0F(DustSensor, CyclicComponent):
    """
    Implements access to the GP2Y1010AU0F dust density sensor.
    WARNING: PROTOTYPE STATUS!
    """

    UPDATE_TIME = 1  # in seconds
    LED_PIN = 17  # BCM - TODO make setting

    def __init__(self, settings: Settings):
        log_values = bool(settings.get(LOG_SENSOR_DATA))
        DustSensor.__init__(self, log_values)
        CyclicComponent.__init__(self, None, settings)
        self._gpio = RPi.GPIO
        self._sensor_driver = None
        self._start_update_loop(self._init_sensor, self._read_sensor)

    def _init_sensor(self):
        """
        Initialize sensor (simply save the module), no complicated init needed.
        """
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn

        self._gpio.setup(self.LED_PIN, self._gpio.OUT)
        i2c = board.I2C()  # uses board.SCL and board.SDA
        # Create the ADC object using the I2C bus
        ads = ADS.ADS1115(i2c)
        # Create single-ended input on channels
        self._sensor_driver = AnalogIn(ads, ADS.P0)

    def _read_sensor(self):
        """
        Reads the actual values in the moving average list.
        Ignores comm. errors, but does simple value validity checks.
        """
        dust_ug_m3 = 0
        try:
            # TODO: Can Python even do such precise timing?
            self._gpio.output(self.LED_PIN, False)  # type: ignore
            time.sleep(0.000280)
            dust = self._sensor_driver.voltage  # type: ignore
            time.sleep(0.000040)
            self._gpio.output(self.LED_PIN, True)  # type: ignore
            time.sleep(0.009680)

        except Exception as error:
            # errors happen fairly often, keep going
            self._logger.error("GP2Y1010AU0F: Can't read sensor - %s", str(error))
            return

        dust_ug_m3 = ((dust * 0.172) - 0.0999) * 1000  # from datasheet V->mg/m3
        self._set_dust(dust_ug_m3)

        self._logger.debug("GP2Y1010AU0F: Dust=%sug/m3", dust_ug_m3)


class SR501(SensorComponent):  # pylint: disable=invalid-name
    """Implements access to the SR501 infrared movement sensor."""

    BOUNCE_TIME = 3

    def __init__(self, pin):
        super().__init__()
        self._pin = pin
        self._motion_detected = 0

        self._sensor_driver: MotionSensor
        if pin == 0:
            self._disabled = True
            return
        self._init_thread = threading.Thread(
            name="SR501_Init", target=self._register_callback, daemon=True
        )
        self._init_thread.start()

    @property
    def motion_detected(self) -> bool:
        """Returns true, if often motion was detected in the last 3 seconds."""
        return bool(self._motion_detected)

    def _register_callback(self):
        """Initializer function, register the wake-up function to the configured pin."""
        try:
            from gpiozero import MotionSensor

            self._sensor_driver = MotionSensor(self._pin)
            self._sensor_driver.when_activated = self._wake_up_from_sensor
        except Exception as error:
            self._disabled = True
            self._logger.error("MotionDetector: sensor cannot be initialized: %s", str(error))

    def _wake_up_from_sensor(self):  # pylint: disable=unused-argument
        """
        Callback function, when pin is high.
        Counting up and waiting is used to smooth out detection.
        """
        self._motion_detected += 1
        self._logger.debug("MotionDetector: motion detected %i", self._motion_detected)
        time.sleep(self.BOUNCE_TIME)
        self._motion_detected -= 1

    def stop(self):
        self._sensor_driver.close()
