from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from waqd.components.weather.base_types import Location
from waqd_website.auth.authentication import user_exception_check
from waqd_website.database import User
from waqd_website.database.weather import clear_user_weather_location
from waqd_website.service.weather_service import weather_service

rt = APIRouter()


class WeatherLocationPayload(BaseModel):
    name: str = ""
    country: str = ""
    state: str = ""
    county: str = ""
    country_code: str = ""
    altitude: float = 0.0
    latitude: float
    longitude: float


class LocationSearchResponse(BaseModel):
    locations: list[WeatherLocationPayload]


class SavedLocationResponse(BaseModel):
    location: Optional[WeatherLocationPayload]


class WebsiteWeatherResponse(BaseModel):
    location: Optional[WeatherLocationPayload]
    current_weather: Optional[dict[str, Any]]
    forecast: list[dict[str, Any]]
    hourly_daytime: list[list[dict[str, Any]]]
    hourly_nighttime: list[list[dict[str, Any]]]
    cached: bool = False


@rt.get("/search", response_model=LocationSearchResponse)
async def search_locations(
    query: str = Query(min_length=2),
    lang: str = Query(default="en", min_length=2, max_length=8),
    current_user: User = user_exception_check,
):
    del current_user
    locations = weather_service.search_locations(query, lang=lang)
    return LocationSearchResponse(
        locations=[WeatherLocationPayload(**location.model_dump()) for location in locations]
    )


@rt.get("/reverse-geocode", response_model=SavedLocationResponse)
async def reverse_geocode(
    latitude: float,
    longitude: float,
    current_user: User = user_exception_check,
):
    del current_user
    resolved = weather_service.resolve_location_name(latitude, longitude)
    return SavedLocationResponse(
        location=None if resolved is None else WeatherLocationPayload(**resolved.model_dump())
    )


@rt.get("/location", response_model=SavedLocationResponse)
async def get_saved_location(current_user: User = user_exception_check):
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="Current user has no id")

    saved_location = weather_service.get_saved_location(current_user.id)
    return SavedLocationResponse(
        location=None
        if saved_location is None
        else WeatherLocationPayload(**saved_location.model_dump())
    )


@rt.put("/location", response_model=SavedLocationResponse)
async def save_location(
    location: WeatherLocationPayload,
    current_user: User = user_exception_check,
):
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="Current user has no id")

    saved_location = weather_service.save_location(
        current_user.id,
        Location(**location.model_dump()),
    )
    return SavedLocationResponse(location=WeatherLocationPayload(**saved_location.model_dump()))


@rt.delete("/location")
async def delete_saved_location(current_user: User = user_exception_check):
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="Current user has no id")

    deleted = clear_user_weather_location(current_user.id)
    return {"deleted": deleted}


@rt.get("/saved-locations", response_model=LocationSearchResponse)
async def get_saved_locations(current_user: User = user_exception_check):
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="Current user has no id")

    locations = weather_service.get_saved_locations_list(current_user.id)
    return LocationSearchResponse(
        locations=[WeatherLocationPayload(**location.model_dump()) for location in locations]
    )


@rt.put("/saved-locations")
async def add_saved_location(
    location: WeatherLocationPayload,
    current_user: User = user_exception_check,
):
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="Current user has no id")

    weather_service.add_saved_location(
        current_user.id,
        Location(**location.model_dump()),
    )
    return {"added": True}


@rt.delete("/saved-locations")
async def remove_saved_location(
    latitude: float,
    longitude: float,
    current_user: User = user_exception_check,
):
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="Current user has no id")

    deleted = weather_service.remove_saved_location(current_user.id, latitude, longitude)
    return {"deleted": deleted}


@rt.get("", response_model=WebsiteWeatherResponse)
async def get_weather(
    force: bool = Query(default=False),
    current_user: User = user_exception_check,
):
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="Current user has no id")

    payload = weather_service.get_weather_for_user(current_user.id, force=force)
    location_payload = payload.get("location")
    return WebsiteWeatherResponse(
        location=None
        if location_payload is None
        else WeatherLocationPayload(**location_payload),
        current_weather=payload.get("current_weather"),
        forecast=payload.get("forecast", []),
        hourly_daytime=payload.get("hourly_daytime", []),
        hourly_nighttime=payload.get("hourly_nighttime", []),
        cached=bool(payload.get("cached", False)),
    )


@rt.get("/preview", response_model=WebsiteWeatherResponse)
async def get_weather_preview(
    latitude: float,
    longitude: float,
    name: str = Query(default=""),
    country: str = Query(default=""),
    state: str = Query(default=""),
    county: str = Query(default=""),
    country_code: str = Query(default=""),
    altitude: float = Query(default=0.0),
    force: bool = Query(default=False),
    current_user: User = user_exception_check,
):
    del current_user

    # Resolve incomplete location data from lat/lon using geo services
    if not country and not state:
        resolved = weather_service.resolve_full_location(latitude, longitude)
        if resolved:
            if not name or name in ("Selected location", "GPS Location"):
                name = resolved.name
            country = resolved.country
            state = resolved.state
            county = resolved.county
            country_code = resolved.country_code
            altitude = resolved.altitude

    location = Location(
        name=name or "Selected location",
        country=country,
        state=state,
        county=county,
        country_code=country_code,
        altitude=altitude,
        latitude=latitude,
        longitude=longitude,
    )

    payload, cached = weather_service.get_weather_for_location(location, force=force)

    return WebsiteWeatherResponse(
        location=WeatherLocationPayload(**location.model_dump()),
        current_weather=payload.get("current_weather"),
        forecast=payload.get("forecast", []),
        hourly_daytime=payload.get("hourly_daytime", []),
        hourly_nighttime=payload.get("hourly_nighttime", []),
        cached=cached,
    )
