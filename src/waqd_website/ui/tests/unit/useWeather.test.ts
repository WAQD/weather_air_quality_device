import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useWeather, type WeatherData } from '../../src/composables/useWeather'

function makeWeather(overrides: Partial<WeatherData> = {}): WeatherData {
  return {
    main: 'clear',
    temp: 20,
    icon: '01d',
    date_time: '2026-08-22T12:00:00',
    wid: 800,
    wind_speed: 3,
    wind_deg: 180,
    sunrise: '06:00:00',
    sunset: '18:00:00',
    pressure: 1013,
    humidity: 50,
    clouds: 0,
    ...overrides,
  }
}

describe('useWeather.isDay', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns true during daylight hours', () => {
    vi.setSystemTime(new Date('2026-08-22T12:00:00'))
    expect(useWeather().isDay(makeWeather())).toBe(true)
  })

  it('returns false before sunrise', () => {
    vi.setSystemTime(new Date('2026-08-22T04:00:00'))
    expect(useWeather().isDay(makeWeather())).toBe(false)
  })

  it('returns false after sunset', () => {
    vi.setSystemTime(new Date('2026-08-22T20:00:00'))
    expect(useWeather().isDay(makeWeather())).toBe(false)
  })

  it('accepts full ISO datetime for sunrise/sunset', () => {
    vi.setSystemTime(new Date('2026-08-22T12:00:00'))
    expect(
      useWeather().isDay(
        makeWeather({
          sunrise: '2026-08-22T06:00:00',
          sunset: '2026-08-22T18:00:00',
        }),
      ),
    ).toBe(true)
  })
})

describe('useWeather.getWeatherBackground', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('maps clear daytime to bg_day_clear.jpg', () => {
    vi.setSystemTime(new Date('2026-08-22T12:00:00'))
    const u = useWeather()
    u.setWeatherData('d1', makeWeather({ main: 'clear' }))
    expect(u.getWeatherBackground('d1').backgroundImage).toContain('bg_day_clear.jpg')
  })

  it('maps clear night to bg_night_clear.jpg', () => {
    vi.setSystemTime(new Date('2026-08-22T23:00:00'))
    const u = useWeather()
    u.setWeatherData('d2', makeWeather({ main: 'clear' }))
    expect(u.getWeatherBackground('d2').backgroundImage).toContain('bg_night_clear.jpg')
  })

  it('maps unknown conditions to clouds', () => {
    vi.setSystemTime(new Date('2026-08-22T12:00:00'))
    const u = useWeather()
    u.setWeatherData('d3', makeWeather({ main: 'hail' }))
    expect(u.getWeatherBackground('d3').backgroundImage).toContain('bg_day_clouds.jpg')
  })

  it('returns an empty object when no weather data exists', () => {
    expect(useWeather().getWeatherBackground('missing')).toEqual({})
  })
})

describe('useWeather store accessors', () => {
  it('sets, gets, checks and clears weather data', () => {
    const u = useWeather()
    const weather = makeWeather()
    expect(u.hasWeatherData('dev')).toBe(false)

    u.setWeatherData('dev', weather)
    expect(u.hasWeatherData('dev')).toBe(true)
    expect(u.getWeatherData('dev')).toEqual(weather)

    u.clearWeatherData('dev')
    expect(u.hasWeatherData('dev')).toBe(false)
    expect(u.getWeatherData('dev')).toBeUndefined()
  })
})
