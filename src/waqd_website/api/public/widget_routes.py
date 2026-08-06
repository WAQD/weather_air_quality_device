from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from waqd.components.weather.base_types import Location
from waqd_website.auth.authentication import get_current_user_from_widget_key
from waqd_website.database import User
from waqd_website.database.weather import get_user_weather_location
from waqd_website.service.weather_service import weather_service

rt = APIRouter()


class WidgetForecastDay(BaseModel):
    day: str
    icon: str
    temp_min: int
    temp_max: int


class WidgetWeatherResponse(BaseModel):
    temp: int
    temp_min: int
    temp_max: int
    main: str
    icon: str
    locationName: str
    updateTime: int
    widget_style: str
    forecast_3_days: list[WidgetForecastDay]


def _empty_location() -> Location:
    return Location(
        name="Unknown",
        country="",
        state="",
        county="",
        country_code="",
        altitude=0.0,
        latitude=0.0,
        longitude=0.0,
    )


@rt.get("/weather", response_model=WidgetWeatherResponse)
async def get_widget_weather(
    user: User = Depends(get_current_user_from_widget_key),
    latitude: Optional[float] = Query(default=None),
    longitude: Optional[float] = Query(default=None),
):
    if latitude is not None and longitude is not None:
        location = _empty_location()
        location.name = "Selected location"
        location.latitude = latitude
        location.longitude = longitude
    else:
        if user.id is None:
            raise HTTPException(status_code=400, detail="User has no id")
        saved = get_user_weather_location(user.id)
        if saved is None:
            raise HTTPException(status_code=400, detail="No saved location for user")
        location = Location(
            name=saved.name,
            country=saved.country,
            state=saved.state,
            county=saved.county,
            country_code=saved.country_code,
            altitude=saved.altitude,
            latitude=saved.latitude,
            longitude=saved.longitude,
        )

    payload, _cached = weather_service.get_weather_for_location(location, force=False)
    current = payload.get("current_weather") or {}
    forecast_list = payload.get("forecast") or []

    resolved_name = location.name
    if resolved_name == "Selected location" or not resolved_name.strip():
        resolved = weather_service.resolve_location_name(
            location.latitude, location.longitude
        )
        if resolved:
            resolved_name = resolved.name

    today_fc = forecast_list[0] if forecast_list else None
    forecast_3: list[WidgetForecastDay] = []
    for day in forecast_list[1:4]:
        import datetime as dt
        date_obj = dt.datetime.fromisoformat(day.get("date_time", ""))
        short_day = date_obj.strftime("%a")
        forecast_3.append(WidgetForecastDay(
            day=short_day,
            icon=day.get("icon", ""),
            temp_min=round(day.get("temp_min", 0)),
            temp_max=round(day.get("temp_max", 0)),
        ))

    condition = ""
    if current.get("main"):
        condition = current["main"]

    import time
    return WidgetWeatherResponse(
        temp=round(current.get("temp", 0)),
        temp_min=round(
            today_fc.get("temp_min", current.get("temp", 0))
            if today_fc
            else current.get("temp", 0)
        ),
        temp_max=round(
            today_fc.get("temp_max", current.get("temp", 0))
            if today_fc
            else current.get("temp", 0)
        ),
        main=condition,
        icon=current.get("icon", ""),
        locationName=resolved_name,
        updateTime=int(time.time() * 1000),
        widget_style="forecast",
        forecast_3_days=forecast_3,
    )
