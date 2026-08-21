from pydantic import BaseModel, Field, field_validator


class ForecastView(BaseModel):
    day_1_label: str = Field(description="Day 1 label", default="Day 1")
    day_1_weather_icon: str = Field(
        description="Weather icon", default="weather_icons/wi-day-sunny.svg"
    )
    day_1_weather_day_min_max: str = Field(description="Day min/max temperature", default="N/A")
    day_1_weather_night_min_max: str = Field(
        description="Night min/max temperature", default="N/A"
    )
    day_2_label: str = Field(description="Day 2 label", default="Day 2")
    day_2_weather_icon: str = Field(
        description="Weather icon", default="weather_icons/wi-cloud.svg"
    )
    day_2_weather_day_min_max: str = Field(description="Day min/max temperature", default="N/A")
    day_2_weather_night_min_max: str = Field(
        description="Night min/max temperature", default="N/A"
    )
    day_3_label: str = Field(description="Day 3 label", default="Day 3")
    day_3_weather_icon: str = Field(
        description="Weather icon", default="weather_icons/wi-cloud.svg"
    )
    day_3_weather_day_min_max: str = Field(description="Day min/max temperature", default="N/A")
    day_3_weather_night_min_max: str = Field(
        description="Night min/max temperature", default="N/A"
    )

    @field_validator("day_1_weather_day_min_max", "day_1_weather_night_min_max", mode="before")
    def set_na_if_inf(cls, v):
        if "inf" in v:
            return "N/A"
        return v

class ExteriorView(BaseModel):
    temp: str = Field(description="Temperature in Celsius", default="N/A")
    hum: str = Field(description="Humidity in %", default="N/A")
    weather_icon: str = Field(
        description="Weather icon", default="weather_icons/wi-cloud.svg"
    )
    weather_day_min_max: str = Field(description="Day min/max temperature", default="N/A")
    weather_night_min_max: str = Field(description="Night min/max temperature", default="N/A")
    background: str = Field(
        description="Background image", default="gui_bgrs/background_s7.jpg"
    )

    @field_validator("weather_day_min_max", "weather_night_min_max", mode="before")
    def set_na_if_inf(cls, v):
        if "inf" in v:
            return "N/A"
        return v