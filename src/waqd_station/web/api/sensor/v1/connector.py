import html
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import waqd_station.app as app
from waqd.components.sensor_base import SensorValueLogger
from waqd.web.api.sensor.v1 import (
    SensorApi_v1,
    SensorApi_v1_1,
    SensorDataPoint,
    SensorHistoryResponse,
)
from waqd_station.web.helper import format_unit_disp_value

if TYPE_CHECKING:
    from pint.facets.plain import PlainQuantity as Quantity

class SensorRetrieval:
    def __init__(self) -> None:
        assert app.comp_ctrl
        self._comps = app.comp_ctrl().components

    def get_exterior_sensor_values(self, units=False) -> SensorApi_v1_1:
        temp = self._comps.remote_exterior_sensor.get_temperature()
        hum = self._comps.remote_exterior_sensor.get_humidity()

        if temp is None or hum is None:
            current_weather = self._comps.weather_info.get_current_weather()
            if current_weather:
                temp = app.unit_reg().Quantity(current_weather.temp, "degC")
                hum = app.unit_reg().Quantity(current_weather.humidity, "percent")
        temp = self._format_sensor_disp_value(temp, units)
        hum = self._format_sensor_disp_value(hum, units, 0)

        data = SensorApi_v1_1(
            temp=temp,
            hum=hum,
        )
        return data

    def _format_sensor_disp_value(
        self, quantity: Optional["Quantity"], unit=False, precision=1
    ):
        disp_value = format_unit_disp_value(quantity, unit, precision)
        return html.escape(disp_value)

    def get_interior_sensor_values(self, units=False) -> SensorApi_v1_1:
        temp = self._comps.temp_sensor.get_temperature()
        hum = self._comps.humidity_sensor.get_humidity()
        pres = self._comps.pressure_sensor.get_pressure()
        co2 = self._comps.co2_sensor.get_co2()

        temp_disp = self._format_sensor_disp_value(temp, units)
        hum = self._format_sensor_disp_value(hum, units, 0)
        pres = self._format_sensor_disp_value(pres, units, 0)
        co2 = self._format_sensor_disp_value(co2, units, 0)

        return SensorApi_v1_1(
            temp=temp_disp, hum=hum, baro=pres, co2=co2, timestamp=datetime.utcnow().isoformat()
        )

    def get_sensor_history(
        self, sensor_location: str, sensor_type: str, hours: int
    ) -> SensorHistoryResponse:
        """
        Retrieve historical sensor data from InfluxDB.

        Args:
            sensor_location: Location type (e.g., 'interior', 'exterior')
            sensor_type: Sensor measurement type (e.g., 'temp_degC', 'humidity_%')
            hours: Number of hours of data to retrieve
        """
        minutes = hours * 60
        time_value_pairs = SensorValueLogger.get_sensor_values(
            sensor_location, sensor_type, minutes_to_read=minutes
        )

        # Determine unit from sensor_type
        unit_map = {
            "temp_degC": "°C",
            "humidity_%": "%",
            "pressure_hPa": "hPa",
            "CO2_ppm": "ppm",
            "TVOC": "ppb",
            "dust_ug_per_m3": "µg/m³",
            "light_lux": "lux",
        }
        unit = unit_map.get(sensor_type, "")

        # Convert to response format
        data_points = [
            SensorDataPoint(timestamp=dt.isoformat(), value=float(value))
            for dt, value in time_value_pairs
        ]

        return SensorHistoryResponse(
            sensor_location=sensor_location,
            sensor_type=sensor_type,
            unit=unit,
            data=data_points,
        )


class SensorWriter:
    def __init__(self) -> None:
        assert app.comp_ctrl
        self._comps = app.comp_ctrl().components

    def write_sensor_values(self, value: SensorApi_v1_1 | SensorApi_v1):
        self._comps.remote_exterior_sensor.read_callback(
            value.temp, value.hum, value.baro, value.co2
        )
