(function() {
  "use strict";
  function formatWidgetPayload(weather, forecast, location, widgetStyle, locale, translateFn = () => void 0) {
    const todayForecast = forecast?.[0];
    const forecast3Days = (forecast?.slice(1, 4) ?? []).map((day) => {
      const dateObj = new Date(day.date_time);
      const shortDay = new Intl.DateTimeFormat(locale, { weekday: "short" }).format(dateObj);
      return {
        day: shortDay,
        icon: day.icon,
        temp_min: Math.round(day.temp_min),
        temp_max: Math.round(day.temp_max)
      };
    });
    let main = "";
    if (weather.wid !== void 0) {
      const key = `weather_${weather.wid}`;
      const t = translateFn(key);
      if (t && t !== key) main = t;
    }
    if (!main && weather.main) {
      const key = `weather_${weather.main.toLowerCase()}`;
      const t = translateFn(key);
      if (t && t !== key) main = t;
      else main = weather.main;
    }
    return {
      temp: Math.round(weather.temp),
      temp_min: todayForecast?.temp_min != null ? Math.round(todayForecast.temp_min) : Math.round(weather.temp),
      temp_max: todayForecast?.temp_max != null ? Math.round(todayForecast.temp_max) : Math.round(weather.temp),
      main,
      icon: weather.icon ?? "",
      locationName: location?.name ?? "Unknown Location",
      updateTime: Date.now(),
      widget_style: widgetStyle,
      forecast_3_days: forecast3Days
    };
  }
  addEventListener("gpsWeatherRefresh", async (resolve, reject) => {
    try {
      const [baseUrlResult, styleResult, localeResult] = await Promise.all([
        CapacitorPreferences.get({ key: "waqd.background.apiBaseUrl" }),
        CapacitorPreferences.get({ key: "waqd.website.widgetStyle" }),
        CapacitorPreferences.get({ key: "waqd.website.locale" })
      ]);
      const baseUrl = baseUrlResult.value ?? "https://waqd.de";
      const widgetStyle = styleResult.value ?? "simple";
      const locale = localeResult.value ?? "en";
      const position = await CapacitorGeolocation.getCurrentPosition({
        enableHighAccuracy: false,
        timeout: 1e4,
        maximumAge: 6e4
      });
      const { latitude, longitude } = position.coords;
      const params = new URLSearchParams({
        latitude: latitude.toString(),
        longitude: longitude.toString(),
        name: "Selected location"
        // Triggers backend reverse geocoding
      });
      const response = await fetch(`${baseUrl}/api/user/weather/preview?${params.toString()}`);
      if (!response.ok) throw new Error(`Weather API returned ${response.status}`);
      const data = await response.json();
      const payload = formatWidgetPayload(
        data.current_weather,
        data.forecast ?? [],
        data.location,
        widgetStyle,
        locale
        // No i18n available in the runner — condition shown as raw string.
      );
      await CapacitorPreferences.set({
        key: "widget_weather_data",
        value: JSON.stringify(payload)
      });
      resolve();
    } catch (err) {
      console.error("[background-runner] gpsWeatherRefresh failed:", err);
      reject(err);
    }
  });
})();
