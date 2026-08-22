import { describe, it, expect } from 'vitest'
import {
  formatWidgetPayload,
  type RawWeatherData,
  type RawForecastDay,
} from '../../src/utils/widgetDataFormatter'

const dayName = (iso: string, locale = 'en') =>
  new Intl.DateTimeFormat(locale, { weekday: 'short' }).format(new Date(iso))

describe('formatWidgetPayload', () => {
  const location = { name: 'Berlin' }
  const weather: RawWeatherData = { temp: 20.4, main: 'Clear', icon: '01d' }
  const forecast: RawForecastDay[] = [
    { date_time: '2026-08-22T12:00:00', icon: '01d', temp_min: 15.2, temp_max: 24.6 },
    { date_time: '2026-08-23T12:00:00', icon: '02d', temp_min: 16.1, temp_max: 25.9 },
    { date_time: '2026-08-24T12:00:00', icon: '10d', temp_min: 14.4, temp_max: 21.3 },
    { date_time: '2026-08-25T12:00:00', icon: '01d', temp_min: 13.0, temp_max: 22.0 },
    { date_time: '2026-08-26T12:00:00', icon: '01d', temp_min: 12.0, temp_max: 20.0 },
  ]

  it('rounds the current temperature', () => {
    const out = formatWidgetPayload(weather, forecast, location, 'simple', 'en')
    expect(out.temp).toBe(20)
  })

  it('takes min/max from today (forecast[0])', () => {
    const out = formatWidgetPayload(weather, forecast, location, 'simple', 'en')
    expect(out.temp_min).toBe(15)
    expect(out.temp_max).toBe(25)
  })

  it('falls back to current temp when forecast is empty', () => {
    const out = formatWidgetPayload(weather, [], location, 'simple', 'en')
    expect(out.temp_min).toBe(20)
    expect(out.temp_max).toBe(20)
  })

  it('builds a 3-day forecast from forecast.slice(1, 4)', () => {
    const out = formatWidgetPayload(weather, forecast, location, 'forecast', 'en')
    expect(out.forecast_3_days).toHaveLength(3)
    expect(out.forecast_3_days[0]).toEqual({
      day: dayName('2026-08-23T12:00:00'),
      icon: '02d',
      temp_min: 16,
      temp_max: 26,
    })
    // slice(1, 4) → index 3 in the original array is the last forecast day
    expect(out.forecast_3_days[2].icon).toBe('01d')
  })

  it('resolves the condition via the wid translateFn', () => {
    const translate = (key: string) => (key === 'weather_800' ? 'Sunny' : undefined)
    const w: RawWeatherData = { ...weather, wid: 800 }
    const out = formatWidgetPayload(w, forecast, location, 'simple', 'en', translate)
    expect(out.main).toBe('Sunny')
  })

  it('falls back to weather.main when wid is not translated', () => {
    const translate = () => undefined
    const w: RawWeatherData = { ...weather, wid: 999, main: 'Clear' }
    const out = formatWidgetPayload(w, forecast, location, 'simple', 'en', translate)
    expect(out.main).toBe('Clear')
  })

  it('uses weather.main (lowercased) as the key when no wid', () => {
    const translate = (key: string) => (key === 'weather_clear' ? 'Klar' : undefined)
    const out = formatWidgetPayload(weather, forecast, location, 'simple', 'en', translate)
    expect(out.main).toBe('Klar')
  })

  it('defaults icon to an empty string', () => {
    const w: RawWeatherData = { ...weather, icon: undefined }
    const out = formatWidgetPayload(w, forecast, location, 'simple', 'en')
    expect(out.icon).toBe('')
  })

  it('defaults locationName to "Unknown Location"', () => {
    const out = formatWidgetPayload(weather, forecast, null, 'simple', 'en')
    expect(out.locationName).toBe('Unknown Location')
  })

  it('passes through the widget style', () => {
    const out = formatWidgetPayload(weather, forecast, location, 'forecast', 'en')
    expect(out.widget_style).toBe('forecast')
  })
})
