import { describe, it, expect } from 'vitest'
import { getFlagIconUrl, formatLocationLabel } from '../../src/utils/weather'
import type { WeatherLocationPayload } from '../../src/composables/useWebsiteWeather'

describe('getFlagIconUrl', () => {
  it('lowercases the country code', () => {
    expect(getFlagIconUrl('DE')).toBe(
      'https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/7.3.2/flags/1x1/de.svg',
    )
  })
})

describe('formatLocationLabel', () => {
  const loc = (overrides: Partial<WeatherLocationPayload>): WeatherLocationPayload => ({
    name: 'Berlin',
    country: 'Germany',
    state: 'Berlin',
    county: '',
    country_code: 'DE',
    altitude: 0,
    latitude: 52.52,
    longitude: 13.405,
    ...overrides,
  })

  it('joins name, state and country', () => {
    expect(formatLocationLabel(loc({}))).toBe('Berlin, Berlin, Germany')
  })

  it('falls back to county when state is empty', () => {
    expect(formatLocationLabel(loc({ state: '', county: 'Berlin County' }))).toBe(
      'Berlin, Berlin County, Germany',
    )
  })

  it('omits empty fields', () => {
    expect(formatLocationLabel(loc({ state: '', county: '' }))).toBe('Berlin, Germany')
  })
})
