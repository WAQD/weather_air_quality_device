import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  useWebsiteWeather,
  type WeatherLocationPayload,
} from '../../src/composables/useWebsiteWeather'
import type { WeatherData } from '../../src/composables/useWeather'

function location(overrides: Partial<WeatherLocationPayload>): WeatherLocationPayload {
  return {
    name: 'Old Town',
    country: 'Germany',
    state: '',
    county: '',
    country_code: 'DE',
    altitude: 0,
    latitude: 48.1,
    longitude: 11.5,
    ...overrides,
  }
}

function weather(temp: number): WeatherData {
  return {
    main: 'clear',
    temp,
    icon: 'wi-day-sunny',
    date_time: '2026-09-14T10:00:00+00:00',
    fetch_time: '2026-09-14T10:00:00+00:00',
    wid: 800,
    wind_speed: 1,
    wind_deg: 0,
    sunrise: '2026-09-14T05:00:00+00:00',
    sunset: '2026-09-14T18:00:00+00:00',
    pressure: 1013,
    humidity: 50,
    clouds: 0,
  }
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function weatherResponse(current: WeatherLocationPayload, temp: number) {
  return {
    location: current,
    current_weather: weather(temp),
    forecast: [],
    hourly_daytime: [],
    hourly_nighttime: [],
    cached: false,
  }
}

const storage = new Map<string, string>()

beforeEach(() => {
  storage.clear()
  vi.stubGlobal('window', {
    localStorage: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value)
      },
    },
  })
  useWebsiteWeather().resetState()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('setHomeLocation', () => {
  it('re-reads the home weather so the home card no longer shows the previous location', async () => {
    const api = useWebsiteWeather()
    const previewed = location({ name: 'Previewed Town', latitude: 50.0, longitude: 8.0 })
    const newHome = location({ name: 'New Town', latitude: 52.5, longitude: 13.4 })

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.toString()
        const method = (init?.method ?? 'GET').toUpperCase()

        if (url.startsWith('/api/user/weather/preview')) {
          return jsonResponse(weatherResponse(previewed, 5))
        }
        if (method === 'PUT' && url.endsWith('/weather/location')) {
          return jsonResponse({ location: newHome })
        }
        if (method === 'PUT') {
          return jsonResponse({ added: true })
        }
        if (url.startsWith('/api/user/weather')) {
          return jsonResponse(weatherResponse(newHome, 21))
        }
        throw new Error(`Unexpected request: ${method} ${url}`)
      }),
    )

    // The user looked at some other location on the weather page first.
    await api.loadWeatherForLocation(previewed)
    expect(api.currentWeather.value?.temp).toBe(5)

    // Saving it as home must refresh the shared home weather state.
    await api.setHomeLocation(newHome)

    expect(api.homeLocation.value?.name).toBe('New Town')
    expect(api.currentWeather.value?.temp).toBe(21)
  })

  it('does not let a late response for the previous home overwrite the new one', async () => {
    const api = useWebsiteWeather()
    const previousHome = location({ name: 'Old Town' })
    const newHome = location({ name: 'New Town', latitude: 52.5, longitude: 13.4 })

    let releaseStaleRequest = () => { }
    const staleGate = new Promise<void>((resolve) => {
      releaseStaleRequest = resolve
    })

    let weatherGetCount = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input.toString()
        const method = (init?.method ?? 'GET').toUpperCase()

        if (method === 'PUT' && url.endsWith('/weather/location')) {
          return jsonResponse({ location: newHome })
        }
        if (method === 'PUT') {
          return jsonResponse({ added: true })
        }
        if (url.startsWith('/api/user/weather')) {
          weatherGetCount += 1
          if (weatherGetCount === 1) {
            // Slow refresh that was started while the old home was still current.
            await staleGate
            return jsonResponse(weatherResponse(previousHome, 12))
          }
          return jsonResponse(weatherResponse(newHome, 21))
        }
        throw new Error(`Unexpected request: ${method} ${url}`)
      }),
    )

    // A weather refresh for the old home is still in flight ...
    const staleRequest = api.loadWeather(false)
    // ... when the user saves a different location as the new home.
    await api.setHomeLocation(newHome)

    expect(api.homeLocation.value?.name).toBe('New Town')
    expect(api.currentWeather.value?.temp).toBe(21)

    // The late response for the old home must not take over the card again.
    releaseStaleRequest()
    await staleRequest

    expect(api.homeLocation.value?.name).toBe('New Town')
    expect(api.currentWeather.value?.temp).toBe(21)
    expect(api.isLoadingWeather.value).toBe(false)
  })
})
