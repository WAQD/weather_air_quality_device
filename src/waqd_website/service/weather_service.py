from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Optional

from waqd.base.file_logger import Logger
from waqd.components.weather.base_types import DailyWeather, Location, Weather
from waqd.components.weather.open_meteo import OpenMeteo
from waqd.components.weather.nominatim import NominatimGeocoding
from waqd.components.weather.open_topo import OpenTopoData
from waqd_website.database.weather import (
    get_user_weather_location,
    save_user_weather_location,
    get_user_saved_locations,
    add_user_saved_location,
    delete_user_saved_location,
)


class WebsiteWeatherService:
    def __init__(self):
        self._search_cache: dict[str, tuple[datetime, list[Location]]] = {}
        self._provider_cache: dict[str, OpenMeteo] = {}
        self._weather_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
        self._fetch_locks: dict[str, Lock] = {}
        self._lock = Lock()
        self._search_ttl = timedelta(hours=12)
        self._weather_ttl = timedelta(minutes=15)

    def search_locations(self, query: str, lang: str = "en") -> list[Location]:
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        cache_key = f"{lang}:{cleaned_query.lower()}"
        now = datetime.now(timezone.utc)

        with self._lock:
            cached = self._search_cache.get(cache_key)
            if cached and cached[0] > now:
                return cached[1]

        locations = OpenMeteo().find_location_candidates(cleaned_query, lang=lang)

        with self._lock:
            self._search_cache[cache_key] = (now + self._search_ttl, locations)

        return locations

    def get_saved_location(self, user_id: int) -> Optional[Location]:
        return get_user_weather_location(user_id)

    def resolve_location_name(self, latitude: float, longitude: float) -> Optional[Location]:
        return NominatimGeocoding().reverse_geocoding(latitude, longitude)

    def resolve_full_location(self, latitude: float, longitude: float) -> Optional[Location]:
        location = NominatimGeocoding().reverse_geocoding(latitude, longitude)
        if location is None:
            return None
        try:
            location.altitude = OpenTopoData().get_altitude(latitude, longitude)
        except Exception:
            location.altitude = 0.0
        return location

    def save_location(self, user_id: int, location: Location) -> Location:
        saved_location = save_user_weather_location(user_id, location)
        self._invalidate_weather_cache(saved_location)
        return saved_location

    def get_saved_locations_list(self, user_id: int) -> list[Location]:
        return get_user_saved_locations(user_id)

    def add_saved_location(self, user_id: int, location: Location) -> None:
        add_user_saved_location(user_id, location)

    def remove_saved_location(self, user_id: int, latitude: float, longitude: float) -> bool:
        return delete_user_saved_location(user_id, latitude, longitude)

    def get_weather_for_user(self, user_id: int, force: bool = False) -> dict[str, Any]:
        location = self.get_saved_location(user_id)
        if location is None:
            return {
                "location": None,
                "current_weather": None,
                "forecast": [],
                "hourly_daytime": [],
                "hourly_nighttime": [],
                "cached": False,
            }

        payload, cached = self.get_weather_for_location(location, force=force)
        payload["location"] = self._serialize_location(location)
        payload["cached"] = cached
        return payload

    def get_weather_for_location(
        self, location: Location, force: bool = False
    ) -> tuple[dict[str, Any], bool]:
        cache_key = self._normalize_location_key(location)
        now = datetime.now(timezone.utc)

        if not force:
            with self._lock:
                cached_entry = self._weather_cache.get(cache_key)
                if cached_entry and cached_entry[0] > now:
                    return cached_entry[1], True

        fetch_lock = self._get_fetch_lock(cache_key)
        with fetch_lock:
            if not force:
                with self._lock:
                    cached_entry = self._weather_cache.get(cache_key)
                    if cached_entry and cached_entry[0] > datetime.now(timezone.utc):
                        return cached_entry[1], True

            provider = self._get_provider(location)
            current_weather = provider.get_current_weather(force=force)
            forecast = provider.get_7_day_forecast(force=force)
            hourly_forecast = [
                provider.get_hourly_forecast(day, force=force) for day in range(7)
            ]

            payload = {
                "current_weather": self._serialize_weather(current_weather),
                "forecast": [self._serialize_daily_weather(day) for day in forecast],
                "hourly_daytime": [],
                "hourly_nighttime": [],
            }

            for day_points in hourly_forecast:
                day_daytime: list[dict[str, Any]] = []
                day_nighttime: list[dict[str, Any]] = []
                for point in day_points:
                    serialized_point = self._serialize_weather(point)
                    assert serialized_point is not None
                    if point.is_daytime():
                        day_daytime.append(serialized_point)
                    else:
                        day_nighttime.append(serialized_point)
                payload["hourly_daytime"].append(day_daytime)
                payload["hourly_nighttime"].append(day_nighttime)

            with self._lock:
                self._weather_cache[cache_key] = (
                    datetime.now(timezone.utc) + self._weather_ttl,
                    payload,
                )

            Logger().info(
                "WebsiteWeather: fetched weather for %s (%s, %s)",
                location.name,
                location.latitude,
                location.longitude,
            )
            return payload, False

    def _get_provider(self, location: Location) -> OpenMeteo:
        cache_key = self._normalize_location_key(location)
        with self._lock:
            provider = self._provider_cache.get(cache_key)
            if provider is None:
                provider = OpenMeteo(longitude=location.longitude, latitude=location.latitude)
                self._provider_cache[cache_key] = provider
            return provider

    def _get_fetch_lock(self, cache_key: str) -> Lock:
        with self._lock:
            existing_lock = self._fetch_locks.get(cache_key)
            if existing_lock is None:
                existing_lock = Lock()
                self._fetch_locks[cache_key] = existing_lock
            return existing_lock

    def _invalidate_weather_cache(self, location: Location):
        cache_key = self._normalize_location_key(location)
        with self._lock:
            self._weather_cache.pop(cache_key, None)

    @staticmethod
    def _normalize_location_key(location: Location) -> str:
        return f"{location.latitude:.3f}:{location.longitude:.3f}"

    @staticmethod
    def _serialize_weather(weather: Optional[Weather]) -> Optional[dict[str, Any]]:
        if weather is None:
            return None
        payload = asdict(weather)
        payload["date_time"] = weather.date_time.isoformat()
        payload["fetch_time"] = weather.fetch_time.isoformat()
        payload["sunrise"] = weather.sunrise.isoformat()
        payload["sunset"] = weather.sunset.isoformat()
        return payload

    @staticmethod
    def _serialize_daily_weather(weather: DailyWeather) -> dict[str, Any]:
        payload = WebsiteWeatherService._serialize_weather(weather)
        assert payload is not None
        payload["temp_min"] = weather.temp_min
        payload["temp_max"] = weather.temp_max
        payload["temp_night_min"] = weather.temp_night_min
        payload["temp_night_max"] = weather.temp_night_max
        payload["precipitation_probability_max"] = weather.precipitation_probability_max
        return payload

    @staticmethod
    def _serialize_location(location: Location) -> dict[str, Any]:
        return location.model_dump()


weather_service = WebsiteWeatherService()
