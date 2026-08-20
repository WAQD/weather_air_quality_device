import type { WeatherLocationPayload } from '../composables/useWebsiteWeather'

export function getFlagIconUrl(countryCode: string): string {
  return `https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/7.3.2/flags/1x1/${countryCode.toLowerCase()}.svg`
}

export function formatLocationLabel(location: WeatherLocationPayload): string {
  return [location.name, location.state || location.county, location.country]
    .filter(Boolean)
    .join(', ')
}
