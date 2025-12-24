from typing import List, Optional
from pydantic import BaseModel, Field


class SensorDataPoint(BaseModel):
    timestamp: str = Field(description="ISO format timestamp")
    value: float = Field(description="Sensor value")


class SensorHistoryResponse(BaseModel):
    sensor_location: str
    sensor_type: str
    unit: str
    data: List[SensorDataPoint]


class SensorApi_v1(BaseModel):
    api_ver: str = "1.0"
    temp: Optional[str] = Field(description="Temperature in Celsius", default="N/A")
    hum: Optional[str] = Field(description="Humidity in %", default="N/A")
    baro: Optional[str] = Field(description="Pressure in hPa", default="N/A")
    co2: Optional[str] = Field(description="CO2 in ppm", default="N/A")
    tvoc: Optional[str] = Field(description="TVOC in ppb", default="N/A")
    dust: Optional[str] = Field(description="Dust in µg/m³", default="N/A")
    light: Optional[str] = Field(description="Light in lux", default="N/A")

class SensorApi_v1_1(BaseModel):
    api_ver: str = "1.1"
    temp: Optional[str] = Field(description="Temperature in Celsius", default="N/A")
    hum: Optional[str] = Field(description="Humidity in %", default="N/A")
    baro: Optional[str] = Field(description="Pressure in hPa", default="N/A")
    co2: Optional[str] = Field(description="CO2 in ppm", default="N/A")
    tvoc: Optional[str] = Field(description="TVOC in ppb", default="N/A")
    dust: Optional[str] = Field(description="Dust in µg/m³", default="N/A")
    light: Optional[str] = Field(description="Light in lux", default="N/A")
    timestamp: Optional[str] = Field(description="ISO format timestamp", default="N/A")

class TempHumSensorApi_v1(SensorApi_v1):
    temp: str = Field(description="Temperature in Celsius", default="N/A")
    hum: str = Field(description="Humidity in %", default="N/A")
