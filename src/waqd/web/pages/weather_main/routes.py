import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from frozendict import frozendict

import waqd.app as app
from waqd.base.assets import get_asset_file_relative
from waqd.settings import LANG
from waqd.web.api.sensor.v1.connector import SensorRetrieval
from waqd.web.api.weather.v1.connector import WeatherRetrieval
from waqd.web.pages.weather_main.model import ExteriorView, ForecastView
from waqd.web.templates import render_main, sub_template
from waqd.base.translation import Translation

rt = APIRouter()

current_path = Path(__file__).parent.resolve()


@rt.get("/", response_class=HTMLResponse)
async def root():
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
    return render_main(content, overflow=False)


@rt.get("/interior")
async def interior():
    # For interior, we redirect to the API endpoint, so we'll handle content comparison there
    # or implement it in the API endpoint itself
    return RedirectResponse(url="/api/sensor/v1/interior?units=True")


@rt.get("/exterior")
async def exterior():
    ext_values = SensorRetrieval().get_exterior_sensor_values(units=True)
    # if not ext_values.temp or hum
    assert ext_values.hum is not None and ext_values.temp is not None
    response_data = ExteriorView(
        temp=ext_values.temp,
        hum=ext_values.hum,
    )
    current_weather = WeatherRetrieval().get_current_weather()
    if not current_weather:
        return JSONResponse(response_data.model_dump())

    weather_bgr = get_asset_file_relative(current_weather.get_background_image())
    forecast = WeatherRetrieval().get_5_day_forecast()

    response_data.background = weather_bgr
    response_data.weather_icon = get_asset_file_relative(current_weather.get_icon())
    response_data.weather_day_min_max = f"{forecast[0].temp_min}°/{forecast[0].temp_max}°"
    response_data.weather_night_min_max = (
        f"{forecast[0].temp_night_min}°/{forecast[0].temp_night_max}°"
    )

    return JSONResponse(content=response_data.model_dump())


@rt.get("/forecast", response_class=JSONResponse)
async def forecast():
    forecast_values = WeatherRetrieval().get_5_day_forecast()
    if not forecast_values:
        # ForecastView with N/A values
        return JSONResponse(ForecastView().model_dump())
    current_date_time = datetime.datetime.now()
    tommorrow_idx = 0
    if forecast_values[0].date_time.date() == current_date_time.date():
        tommorrow_idx = 1
    response_data = ForecastView(
        # determine the next days indexes based on the current date
        day_1_label=Translation().get_localized_date(
            current_date_time + datetime.timedelta(days=1), app.settings.get_string(LANG)
        ),
        day_1_weather_icon=get_asset_file_relative(forecast_values[0].get_icon()),
        day_1_weather_day_min_max=f"{forecast_values[tommorrow_idx].temp_min}°/{forecast_values[tommorrow_idx].temp_max}°",
        day_1_weather_night_min_max=f"{forecast_values[tommorrow_idx].temp_night_min}°/{forecast_values[tommorrow_idx].temp_night_max}°",
        day_2_label=Translation().get_localized_date(
            current_date_time + datetime.timedelta(days=2), app.settings.get_string(LANG)
        ),
        day_2_weather_icon=get_asset_file_relative(forecast_values[1].get_icon()),
        day_2_weather_day_min_max=f"{forecast_values[tommorrow_idx + 1].temp_min}°/{forecast_values[tommorrow_idx + 1].temp_max}°",
        day_2_weather_night_min_max=f"{forecast_values[tommorrow_idx + 1].temp_night_min}°/{forecast_values[tommorrow_idx + 1].temp_night_max}°",
        day_3_label=Translation().get_localized_date(
            current_date_time + datetime.timedelta(days=3), app.settings.get_string(LANG)
        ),
        day_3_weather_icon=get_asset_file_relative(forecast_values[2].get_icon()),
        day_3_weather_day_min_max=f"{forecast_values[tommorrow_idx + 2].temp_min}°/{forecast_values[tommorrow_idx + 2].temp_max}°",
        day_3_weather_night_min_max=f"{forecast_values[tommorrow_idx + 2].temp_night_min}°/{forecast_values[tommorrow_idx + 2].temp_night_max}°",
    )

    return JSONResponse(content=response_data.model_dump())
