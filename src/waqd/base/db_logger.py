import os
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from waqd import LOCAL_TIMEZONE
from waqd.base.file_logger import Logger

from influxdb_client import InfluxDBClient, Point, WritePrecision  # type: ignore
from influxdb_client.client.write_api import SYNCHRONOUS


INFLUX_DB_ORG = "waqd-local"
INFLUX_DB_BUCKET = "waqd-test"


class InfluxSensorLogger:
    _token = ""
    _enabled = True
    _initialized = False
    """ Emulate Logger class with info to log and get_sensor_values"""

    @classmethod
    def __init__(cls):
        if not cls._enabled or cls._initialized:
            return
        config_file = Path().home() / ".influxdbv2/configs"
        if not config_file.is_file():
            cls.setup_db()
        parser = ConfigParser()
        try:
            parser.read(config_file)
            default_entry = parser["default"]
            org = default_entry.get("org", "").replace('"', "")
            assert org == "waqd-local"
            assert default_entry.get("active") == "true"
            cls._token = default_entry.get("token", "").replace('"', "")
        except Exception as e:
            Logger().error(f"SensorDB: {str(e)}")
            cls._enabled = False
            return
        # Try bucket
        with InfluxDBClient(url="http://localhost:8086", token=cls._token, org=org) as client:
            try:
                if not client.buckets_api().find_bucket_by_name(INFLUX_DB_BUCKET):
                    client.buckets_api().create_bucket(INFLUX_DB_BUCKET)
            except Exception as e:
                Logger().error(f"SensorDB: {str(e)}")
                cls._enabled = False
        cls._initialized = True

    @staticmethod
    def setup_db():
        os.system(
            "influx setup -org waqd-local --bucket waqd-test --username waqd-local-user --password ExAmPl3PA55W0rD --force"
        )

    @classmethod
    def set_value(
        cls, sensor_location: str, sensor_type: str, value: Optional[float], time=None
    ):
        if not cls._enabled:
            return
        if value is None:
            return
        if time is None:
            time = datetime.now(LOCAL_TIMEZONE)
        InfluxSensorLogger()  # do setup if not initialized
        with InfluxDBClient(
            url="http://localhost:8086", token=cls._token, org=INFLUX_DB_ORG
        ) as client:
            write_api = client.write_api(write_options=SYNCHRONOUS)
            point = (
                Point("air_quality")
                .tag("type", sensor_location)
                .field(sensor_type, float(value))
                .time(time, WritePrecision.S)
            )
            try:
                write_api.write(INFLUX_DB_BUCKET, INFLUX_DB_ORG, point)
            except Exception as e:
                Logger().error(f"SensorDB: {str(e)}")
            write_api.close()

    @classmethod
    def get_sensor_values(
        cls,
        sensor_location: str,
        sensor_type: str,
        minutes_to_read: int = 180,
        last_value=False,
    ) -> List[Tuple[datetime, float]]:
        # zero reads the last value
        if not cls._enabled:
            return []
        tables = None
        InfluxSensorLogger()  # do setup if not initialized
        try:
            with InfluxDBClient(
                url="http://localhost:8086", token=cls._token, org=INFLUX_DB_ORG
            ) as client:
                filter_expression = f"range(start: -{str(minutes_to_read)}m)"
                if last_value:
                    filter_expression += " |> last()"
                else:
                    # Add intelligent downsampling based on time range
                    # Goal: ~200-300 data points max for optimal chart rendering
                    if minutes_to_read <= 360:  # Up to 6 hours
                        window_size = "2m"  # ~180 points
                    elif minutes_to_read <= 720:  # Up to 12 hours
                        window_size = "3m"  # ~240 points
                    elif minutes_to_read <= 1440:  # Up to 24 hours
                        window_size = "5m"  # ~288 points
                    elif minutes_to_read <= 2880:  # Up to 48 hours
                        window_size = "10m"  # ~288 points
                    elif minutes_to_read <= 10080:  # Up to 7 days
                        window_size = "30m"  # ~336 points
                    else:  # More than 7 days
                        window_size = "1h"  # Hourly aggregation
                    
                    # Use aggregateWindow to downsample with mean
                    filter_expression += (
                        f' |> aggregateWindow(every: {window_size}, '
                        'fn: mean, createEmpty: false)'
                    )
                
                query = (
                    f'from(bucket: "{INFLUX_DB_BUCKET}") |> {filter_expression}'
                    f'|> filter(fn: (r) => r["type"] == "{sensor_location}")'
                    f'|> filter(fn: (r) => r["_field"] == "{sensor_type}")'
                    '|> filter(fn: (r) => r["_measurement"] == "air_quality")'
                )
                tables = client.query_api().query(query, org=INFLUX_DB_ORG)
        except Exception as e:
            Logger().error(
                f"Error while quering {sensor_location} {sensor_type} from InfluxDB: {str(e)}"
            )
            return []
        time_value_pairs: List[Tuple[datetime, float]] = []
        for table in tables:
            for record in table.records:
                time_value_pairs.append((record.get_time(), float(record.get_value())))

        return time_value_pairs
