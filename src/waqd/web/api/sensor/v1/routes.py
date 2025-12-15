from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from .connector import SensorRetrieval, SensorWriter
from .model import SensorApi_v1, SensorHistoryResponse

rt = APIRouter()


@rt.get("/interior", response_class=JSONResponse)
async def get_interior(units: bool = False) -> SensorApi_v1:
    values = SensorRetrieval().get_interior_sensor_values(units=units)
    return values


@rt.get("/exterior", response_class=JSONResponse)
async def get_exterior(units: bool = False) -> SensorApi_v1:
    values = SensorRetrieval().get_exterior_sensor_values(units=units)
    return values

@rt.post("/interior", response_class=JSONResponse)
async def post_interior(values: SensorApi_v1):
    SensorWriter().write_sensor_values(values)

@rt.post("/exterior", response_class=JSONResponse)
async def post_exterior(values: SensorApi_v1):
    SensorWriter().write_sensor_values(values)


@rt.get("/history", response_class=JSONResponse)
async def get_sensor_history(
    sensor_location: str,
    sensor_type: str,
    hours: int = 12
) -> SensorHistoryResponse:
    """
    Get historical sensor data from InfluxDB.
    
    Args:
        sensor_location: Location type (e.g., 'interior', 'exterior')
        sensor_type: Sensor measurement type (e.g., 'temp_degC', 'humidity_%', 'CO2_ppm')
        hours: Number of hours of historical data to retrieve (default: 12)
    """
    try:
        history = SensorRetrieval().get_sensor_history(
            sensor_location, sensor_type, hours
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
