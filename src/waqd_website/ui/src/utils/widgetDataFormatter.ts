/**
 * Pure utility for formatting weather data into the Android widget payload.
 * No Vue, no DOM, no i18n instance — safe to use everywhere.
 */

export interface WidgetForecastDay {
  day: string
  icon: string
  temp_min: number
  temp_max: number
}

export interface WidgetWeatherPayload {
  temp: number
  temp_min: number
  temp_max: number
  main: string
  icon: string
  locationName: string
  updateTime: number
  widget_style: string
  forecast_3_days: WidgetForecastDay[]
}

export interface RawWeatherData {
  temp: number
  wid?: number
  main?: string
  icon?: string
}

export interface RawForecastDay {
  date_time: string
  icon: string
  temp_min: number
  temp_max: number
}

export interface RawLocation {
  name?: string
}

/**
 * Formats the raw API payload into the shape expected by WeatherWidgetProvider.java.
 *
 * @param weather       Current weather object from the API response.
 * @param forecast      Array of daily forecast objects (index 0 = today).
 * @param location      Location object (may be null).
 * @param widgetStyle   'simple' | 'forecast' — stored in Preferences.
 * @param locale        BCP-47 locale string (e.g. 'en', 'de').
 * @param translateFn   Optional translation callback. Receives a key like
 *                      'weather_800' or 'weather_clear sky' and should return
 *                      the translated string or undefined if not found.
 */
export function formatWidgetPayload(
  weather: RawWeatherData,
  forecast: RawForecastDay[],
  location: RawLocation | null,
  widgetStyle: string,
  locale: string,
  translateFn: (key: string) => string | undefined = () => undefined,
): WidgetWeatherPayload {
  const todayForecast = forecast?.[0]

  const forecast3Days: WidgetForecastDay[] = (forecast?.slice(1, 4) ?? []).map((day) => {
    const dateObj = new Date(day.date_time)
    const shortDay = new Intl.DateTimeFormat(locale, { weekday: 'short' }).format(dateObj)
    return {
      day: shortDay,
      icon: day.icon,
      temp_min: Math.round(day.temp_min),
      temp_max: Math.round(day.temp_max),
    }
  })

  // Resolve human-readable condition string via optional translateFn.
  let main = ''
  if (weather.wid !== undefined) {
    const key = `weather_${weather.wid}`
    const t = translateFn(key)
    if (t && t !== key) main = t
  }
  if (!main && weather.main) {
    const key = `weather_${weather.main.toLowerCase()}`
    const t = translateFn(key)
    if (t && t !== key) main = t
    else main = weather.main
  }

  return {
    temp: Math.round(weather.temp),
    temp_min: todayForecast?.temp_min != null ? Math.round(todayForecast.temp_min) : Math.round(weather.temp),
    temp_max: todayForecast?.temp_max != null ? Math.round(todayForecast.temp_max) : Math.round(weather.temp),
    main,
    icon: weather.icon ?? '',
    locationName: location?.name ?? 'Unknown Location',
    updateTime: Date.now(),
    widget_style: widgetStyle,
    forecast_3_days: forecast3Days,
  }
}
