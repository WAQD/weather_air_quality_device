import datetime
import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from frozendict import frozendict

import waqd.app as app
from waqd.assets.assets import get_asset_file_relative
from waqd.settings import LANG
from waqd.web.api.sensor.v1.connector import SensorRetrieval
from waqd.web.api.weather.v1.connector import WeatherRetrieval
from waqd.web.authentication import User, user_exception_check, user_redirect_check
from waqd.web.helper import get_localized_date
from waqd.web.pages.weather_main.model import ExteriorView, ForecastView
from waqd.web.templates import render_main, sub_template
from waqd.base.translation import Translation

rt = APIRouter()

current_path = Path(__file__).parent.resolve()

@rt.get("/", response_class=HTMLResponse)
async def root(current_user: Annotated[User, user_redirect_check]):
    app.comp_ctrl.init_all()
    lang_val = app.settings.get_string(LANG)
    content = sub_template(
        "waqd.html",
        {
            "cards": tuple(
                [
                    frozendict(
                        {
                            "id": "Interior",
                            "name": Translation().get_localized_string(
                                "ui_dict.json", "card_interior", lang_val
                            ),
                            "background": "/static/gui_bgrs/background_interior2.jpg",
                            "endpoint": "/weather/interior",
                        }
                    ),
                    frozendict(
                        {
                            "id": "Exterior",
                            "name": Translation().get_localized_string(
                                "ui_dict.json", "card_exterior", lang_val
                            ),
                            "background": "",
                            "endpoint": "/weather/exterior",
                        }
                    ),
                    frozendict(
                        {
                            "id": "Forecast",
                            "name": Translation().get_localized_string(
                                "ui_dict.json", "card_forecast", lang_val
                            ),
                            "background": "/static/gui_bgrs/background_s7.jpg",
                            "endpoint": "/weather/forecast",
                        }
                    ),
                ]
            )
        },
        current_path,
    )
    return render_main(content, current_user, overflow=False)


@rt.get("/interior")
async def interior(
    user=user_exception_check,
):
    # For interior, we redirect to the API endpoint, so we'll handle content comparison there
    # or implement it in the API endpoint itself
    return RedirectResponse(url="/api/sensor/v1/interior?units=True")


@rt.get("/exterior")
async def exterior(
    user=user_exception_check,
):
    ext_values = SensorRetrieval().get_exterior_sensor_values(units=True)
    current_weather = WeatherRetrieval().get_current_weather()
    forecast = WeatherRetrieval().get_5_day_forecast()
    if not current_weather:
        return JSONResponse(content=ExteriorView().model_dump())

    weather_bgr = get_asset_file_relative(current_weather.get_background_image())
    response_data = ExteriorView(
        background=weather_bgr,
        temp=ext_values.temp,
        hum=ext_values.hum,
        weather_icon=get_asset_file_relative(current_weather.get_icon()),
        weather_day_min_max=f"{forecast[0].temp_min}°/{forecast[0].temp_max}°",
        weather_night_min_max=f"{forecast[0].temp_night_min}°/{forecast[0].temp_night_max}°",
    )

    return JSONResponse(content=response_data.model_dump())


@rt.get("/forecast", response_class=JSONResponse)
async def forecast(
    user=user_exception_check,
):
    forecast = WeatherRetrieval().get_5_day_forecast()
    current_date_time = datetime.datetime.now()
    tommorrow_idx = 0
    if forecast[0].date_time.date() == current_date_time.date():
        tommorrow_idx = 1
    response_data = ForecastView(
        # determine the next days indexes based on the current date
        day_1_label=get_localized_date(
            current_date_time + datetime.timedelta(days=1), app.settings
        ),
        day_1_weather_icon=get_asset_file_relative(forecast[0].get_icon()),
        day_1_weather_day_min_max=f"{forecast[tommorrow_idx].temp_min}°/{forecast[tommorrow_idx].temp_max}°",
        day_1_weather_night_min_max=f"{forecast[tommorrow_idx].temp_night_min}°/{forecast[tommorrow_idx].temp_night_max}°",
        day_2_label=get_localized_date(
            current_date_time + datetime.timedelta(days=2), app.settings
        ),
        day_2_weather_icon=get_asset_file_relative(forecast[1].get_icon()),
        day_2_weather_day_min_max=f"{forecast[tommorrow_idx + 1].temp_min}°/{forecast[tommorrow_idx + 1].temp_max}°",
        day_2_weather_night_min_max=f"{forecast[tommorrow_idx + 1].temp_night_min}°/{forecast[tommorrow_idx + 1].temp_night_max}°",
        day_3_label=get_localized_date(
            current_date_time + datetime.timedelta(days=3), app.settings
        ),
        day_3_weather_icon=get_asset_file_relative(forecast[2].get_icon()),
        day_3_weather_day_min_max=f"{forecast[tommorrow_idx + 2].temp_min}°/{forecast[tommorrow_idx + 2].temp_max}°",
        day_3_weather_night_min_max=f"{forecast[tommorrow_idx + 2].temp_night_min}°/{forecast[tommorrow_idx + 2].temp_night_max}°",
    )

    return JSONResponse(content=response_data.model_dump())


@rt.get("/forecast/daily/1", response_class=HTMLResponse)
async def forecast_1(
    user=user_exception_check,
):
    content = sub_template("forecast_1.html", {}, current_path, True)
    return content
