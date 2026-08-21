import waqd_station.app as app


class WeatherRetrieval:
    def __init__(self) -> None:
        assert app.comp_ctrl
        self._comps = app.comp_ctrl().components

    def get_current_weather(self):
        return self._comps.weather_info.get_current_weather()

    def get_7_day_forecast(self):
        return self._comps.weather_info.get_7_day_forecast()
