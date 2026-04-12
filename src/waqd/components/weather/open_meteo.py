from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from .base_types import (
    DailyWeather,
    Location,
    Weather,
    WeatherProvider,
)
from .icon_mapping import om_condition_map, om_day_code_to_ico, om_night_code_to_ico


class OpenMeteo(WeatherProvider):
    API_FORECAST_CMD = (
        "https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
    )
    API_GEOCODING_CMD = (
        "https://geocoding-api.open-meteo.com/v1/search?name={query}&language={lang}"
    )

    def __init__(
        self,
        longitude=0.0,
        latitude=0.0,
        geocoding_fetch_rate_seconds: int = 30,
        daily_fetch_rate_seconds: int = 15 * 60,
        hourly_fetch_rate_seconds: int = 5 * 60,
    ):
        super().__init__()
        self._longitude = longitude
        self._latitude = latitude
        self._current_weather: Optional[Weather] = None
        self._seven_day_forecast: List[DailyWeather] = []
        self._hourly_forecast: List[List[Weather]] = [[] for _ in range(7)]
        self._ready = True

        self._geocoding_fetch_rate_seconds = geocoding_fetch_rate_seconds
        self._daily_fetch_rate_seconds = daily_fetch_rate_seconds
        self._hourly_fetch_rate_seconds = hourly_fetch_rate_seconds

        self._last_geocoding_fetch: Dict[str, datetime] = {}
        self._last_daily_fetch: Optional[datetime] = None
        self._last_hourly_fetch: Optional[datetime] = None

        self._geocoding_cache: Dict[str, List[Location]] = {}

    def set_fetch_rates(
        self,
        geocoding_fetch_rate_seconds: Optional[int] = None,
        daily_fetch_rate_seconds: Optional[int] = None,
        hourly_fetch_rate_seconds: Optional[int] = None,
    ) -> None:
        if geocoding_fetch_rate_seconds is not None:
            self._geocoding_fetch_rate_seconds = geocoding_fetch_rate_seconds
        if daily_fetch_rate_seconds is not None:
            self._daily_fetch_rate_seconds = daily_fetch_rate_seconds
        if hourly_fetch_rate_seconds is not None:
            self._hourly_fetch_rate_seconds = hourly_fetch_rate_seconds

    def find_location_candidates(self, query: str, lang="en", force=False) -> List[Location]:
        cache_key = f"{lang}:{query.strip().lower()}"
        if (
            not force
            and cache_key in self._geocoding_cache
            and not self._should_fetch(
                self._last_geocoding_fetch.get(cache_key),
                self._geocoding_fetch_rate_seconds,
            )
        ):
            return self._geocoding_cache[cache_key]

        data = self._call_api(self.API_GEOCODING_CMD, query=quote(query), lang=lang)
        locations = []
        for result in data.get("results", []):
            locations.append(
                Location(
                    name=result.get("name", ""),
                    country=result.get("country", ""),
                    country_code=result.get("country_code", ""),
                    state=result.get("admin1", ""),
                    county=result.get("admin2", ""),
                    altitude=result.get("elevation", 0),
                    latitude=result.get("latitude", 0),
                    longitude=result.get("longitude", 0),
                )
            )

        self._geocoding_cache[cache_key] = locations
        self._last_geocoding_fetch[cache_key] = datetime.now()
        return locations

    def get_current_weather(self, force=False) -> Optional[Weather]:
        """Public API function to get the current weather."""
        self._fetch_weather(force=force, include_hourly=True)
        return self._current_weather

    def get_7_day_forecast(self, force=False) -> List[DailyWeather]:
        self._fetch_weather(force=force, include_hourly=True)
        return self._seven_day_forecast

    def get_hourly_forecast(self, day: int, force=False) -> List[Weather]:
        self._fetch_weather(force=force, include_hourly=True)
        if day < 0 or day >= len(self._hourly_forecast):
            return []
        return self._hourly_forecast[day]

    def _fetch_weather(self, force=False, include_hourly=False):
        if force or self._should_fetch(self._last_daily_fetch, self._daily_fetch_rate_seconds):
            self._fetch_daily_weather()

        if include_hourly and (
            force
            or self._should_fetch(self._last_hourly_fetch, self._hourly_fetch_rate_seconds)
        ):
            self._fetch_hourly_weather()

    def _fetch_daily_weather(self):
        response = self._call_api(
            self.API_FORECAST_CMD
            + "&daily=precipitation_probability_max,weathercode,temperature_2m_max,"
            + "temperature_2m_min,sunrise,sunset,precipitation_sum,"
            + "rain_sum,showers_sum,snowfall_sum,precipitation_hours,windspeed_10m_max,"
            + "winddirection_10m_dominant&current_weather=true&windspeed_unit=ms&timezone=auto",
            latitude=self._latitude,
            longitude=self._longitude,
        )
        if not response:
            return

        self._seven_day_forecast = []
        current_weather = response.get("current_weather", {})
        daily = response.get("daily", {})

        for i in range(len(daily.get("time", []))):
            sunrise = datetime.fromisoformat(daily.get("sunrise", [])[i]).time()
            sunset = datetime.fromisoformat(daily.get("sunset", [])[i]).time()
            daily_weather = DailyWeather(
                self._get_main_category(daily.get("weathercode", [])[i]),
                daily.get("weathercode", [])[i],
                datetime.fromisoformat(daily.get("time", [])[i]),
                self._get_icon_name(daily.get("weathercode", [])[i], True),
                daily.get("windspeed_10m_max", [])[i],
                daily.get("winddirection_10m_dominant", [])[i],
                sunrise,
                sunset,
                0,
                0,
                0,
                0,
                0,
                response.get(
                    "elevation",
                    0,
                ),
                daily.get("precipitation_sum", [0])[i],
                daily.get("precipitation_probability_max", [0])[i],
            )
            daily_weather.temp_min = daily.get("temperature_2m_min", [])[i]
            daily_weather.temp_max = daily.get("temperature_2m_max", [])[i]
            daily_weather.temp_night_min = daily.get("temperature_2m_min", [])[i]
            daily_weather.temp_night_max = daily.get("temperature_2m_min", [])[i]
            daily_weather.precipitation_probability_max = daily.get(
                "precipitation_probability_max", [0]
            )[i]
            self._seven_day_forecast.append(daily_weather)

        if not self._seven_day_forecast:
            self._logger.warning("OpenMeteo: No daily forecast weather data received")
            return

        sunrise = self._seven_day_forecast[0].sunrise
        sunset = self._seven_day_forecast[0].sunset
        is_day = current_weather.get("is_day", 1) == 1
        self._current_weather = Weather(
            self._get_main_category(current_weather.get("weathercode", 0)),
            current_weather.get("weathercode", 0),
            datetime.now(),
            self._get_icon_name(current_weather.get("weathercode", 0), is_day),
            current_weather.get("windspeed", 0.0),
            current_weather.get("winddirection", 0.0),
            sunrise,
            sunset,
            0.0,
            0.0,
            0.0,
            0.0,
            current_weather.get("temperature", 0.0),
            response.get("elevation", 0),
            current_weather.get("precipitation", 0.0),
            0.0,
        )
        self._last_daily_fetch = datetime.now()

    def _fetch_hourly_weather(self):
        if not self._seven_day_forecast:
            return

        response = self._call_api(
            self.API_FORECAST_CMD
            + "&hourly=precipitation_probability,temperature_2m,relativehumidity_2m,"
            + "precipitation,cloudcover,weathercode,pressure_msl,surface_pressure,"
            + "windspeed_10m,winddirection_10m,is_day&windspeed_unit=ms&timezone=auto",
            latitude=self._latitude,
            longitude=self._longitude,
        )
        if not response:
            return

        hourly_forecast: List[List[Weather]] = [[] for _ in range(7)]
        day_temps: List[List[float]] = [[] for _ in range(7)]
        night_temps: List[List[float]] = [[] for _ in range(7)]

        current_datetime = datetime.now()
        hourly = response.get("hourly", {})

        for i in range(len(hourly.get("time", []))):
            entry_date_time = datetime.fromisoformat(hourly.get("time", [])[i])
            if entry_date_time < current_datetime:
                continue

            time_delta = entry_date_time.date() - current_datetime.date()
            day_idx = time_delta.days
            if day_idx < 0 or day_idx >= len(hourly_forecast):
                continue

            if day_idx >= len(self._seven_day_forecast):
                continue

            day_info = self._seven_day_forecast[day_idx]
            is_day = hourly.get("is_day", [1])[i] == 1
            weather_point = Weather(
                self._get_main_category(hourly.get("weathercode", [i])[i]),
                hourly.get("weathercode", [i])[i],
                entry_date_time,
                self._get_icon_name(hourly.get("weathercode", [])[i], is_day),
                hourly.get("windspeed_10m", [])[i],
                hourly.get("winddirection_10m", [])[i],
                day_info.sunrise,
                day_info.sunset,
                hourly.get("surface_pressure", [])[i],
                hourly.get("pressure_msl", [])[i],
                hourly.get("relativehumidity_2m", [])[i],
                hourly.get("cloudcover", [])[i],
                hourly.get("temperature_2m", [])[i],
                day_info.altitude,
                hourly.get("precipitation", [])[i],
                hourly.get("precipitation_probability", [])[i],
            )
            hourly_forecast[day_idx].append(weather_point)

            if is_day:
                day_temps[day_idx].append(weather_point.temp)
            else:
                night_temps[day_idx].append(weather_point.temp)

        self._hourly_forecast = hourly_forecast
        self._set_min_max_temps(day_temps, night_temps)
        self._update_current_weather_from_hourly()
        self._last_hourly_fetch = datetime.now()

    def _set_min_max_temps(
        self,
        daytime_temps: List[List[float]],
        nighttime_temps: List[List[float]],
    ):
        max_days = min(len(self._seven_day_forecast), len(daytime_temps), len(nighttime_temps))

        for day_idx in range(max_days):
            day_values = daytime_temps[day_idx]
            if day_values:
                self._seven_day_forecast[day_idx].temp_max = max(day_values)
                self._seven_day_forecast[day_idx].temp_min = min(day_values)

            night_values = nighttime_temps[day_idx]
            if night_values:
                self._seven_day_forecast[day_idx].temp_night_max = max(night_values)
                self._seven_day_forecast[day_idx].temp_night_min = min(night_values)

    def _update_current_weather_from_hourly(self):
        if (
            not self._current_weather
            or not self._hourly_forecast
            or not self._hourly_forecast[0]
        ):
            return

        now = datetime.now()
        point = next((p for p in self._hourly_forecast[0] if p.date_time >= now), None)
        if point is None:
            point = self._hourly_forecast[0][-1]

        self._current_weather.humidity = point.humidity
        self._current_weather.clouds = point.clouds
        self._current_weather.pressure = point.pressure
        self._current_weather.pressure_sea_level = point.pressure_sea_level
        self._current_weather.precipitation = point.precipitation

    @staticmethod
    def _should_fetch(last_fetch: Optional[datetime], fetch_rate_seconds: int) -> bool:
        if last_fetch is None:
            return True
        return (datetime.now() - last_fetch).total_seconds() >= fetch_rate_seconds

    def _call_api(self, command: str, **kwargs) -> Dict[str, Any]:
        """Call the REST like API of OpenWeatherMap. Return response."""
        if self._disabled:
            return {}

        try:
            command = command.format(**kwargs)
            response = requests.get(command, timeout=5)
            if response.ok:
                return response.json()
        except Exception as error:
            self._logger.error("OpenMeteo: Can't get data: %s", str(error))
        return {}

    def _get_icon_name(self, ident: int, is_day=False) -> str:
        """
        Helper function to get icon from condition.
        """
        if is_day:
            icon_name = om_day_code_to_ico.get(ident, "")
        else:
            icon_name = om_night_code_to_ico.get(ident, "")
        return icon_name

    def _get_main_category(self, ident: int) -> str:
        return om_condition_map.get(ident, "unknown")
