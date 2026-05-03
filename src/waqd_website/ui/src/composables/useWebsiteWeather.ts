import { computed, ref, watch } from 'vue'
import { Preferences } from '@capacitor/preferences'
import type { AvailableLocale } from '../i18n'
import i18n from '../i18n'
import type { ForecastData, HourlyWeatherData, WeatherData } from './useWeather'

export interface WeatherLocationPayload {
  name: string
  country: string
  state: string
  county: string
  country_code: string
  altitude: number
  latitude: number
  longitude: number
}

interface SavedLocationResponse {
  location: WeatherLocationPayload | null
}

interface LocationSearchResponse {
  locations: WeatherLocationPayload[]
}

interface WebsiteWeatherResponse {
  location: WeatherLocationPayload | null
  current_weather: WeatherData | null
  forecast: ForecastData[]
  hourly_daytime: HourlyWeatherData[][]
  hourly_nighttime: HourlyWeatherData[][]
  cached: boolean
}

const SAVED_LOCATIONS_KEY = 'waqd.website.savedLocations'

const savedLocation = ref<WeatherLocationPayload | null>(null)
const savedLocations = ref<WeatherLocationPayload[]>([])
const currentLocation = ref<WeatherLocationPayload | null>(null)
const homeLocation = ref<WeatherLocationPayload | null>(null)
const currentWeather = ref<WeatherData | null>(null)
const forecastData = ref<ForecastData[]>([])
const hourlyDaytimeData = ref<HourlyWeatherData[][]>([])
const hourlyNighttimeData = ref<HourlyWeatherData[][]>([])
const searchResults = ref<WeatherLocationPayload[]>([])
const isLoadingLocation = ref(false)
const isLoadingWeather = ref(false)
const isSearching = ref(false)
const isSavingLocation = ref(false)
const cached = ref(false)
const errorMessage = ref('')
let activeSearchController: AbortController | null = null
let searchRequestSequence = 0

function getLocationKey(location: WeatherLocationPayload): string {
  return `${location.latitude.toFixed(4)}:${location.longitude.toFixed(4)}`
}

function readLocalSavedLocations(): WeatherLocationPayload[] {
  try {
    const raw = window.localStorage.getItem(SAVED_LOCATIONS_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw) as WeatherLocationPayload[]
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter((item) => typeof item?.latitude === 'number' && typeof item?.longitude === 'number')
  } catch {
    return []
  }
}

function writeLocalSavedLocations(locations: WeatherLocationPayload[]): void {
  window.localStorage.setItem(SAVED_LOCATIONS_KEY, JSON.stringify(locations))
}

function upsertSavedLocation(location: WeatherLocationPayload): void {
  const key = getLocationKey(location)
  const withoutExisting = savedLocations.value.filter((item) => getLocationKey(item) !== key)
  savedLocations.value = [location, ...withoutExisting]
  writeLocalSavedLocations(savedLocations.value)
}

function removeSavedLocationEntry(location: WeatherLocationPayload): void {
  const key = getLocationKey(location)
  savedLocations.value = savedLocations.value.filter((item) => getLocationKey(item) !== key)
  writeLocalSavedLocations(savedLocations.value)
}

async function extractErrorMessage(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = await response.json()
    if (typeof payload?.detail === 'string' && payload.detail.trim()) {
      return payload.detail
    }
  } catch {
    // Ignore JSON parsing failures and fall back to a generic message.
  }

  return `${fallbackMessage} (${response.status})`
}

function resetWeatherData(): void {
  currentWeather.value = null
  forecastData.value = []
  hourlyDaytimeData.value = []
  hourlyNighttimeData.value = []
  cached.value = false
}

function clearError(): void {
  errorMessage.value = ''
}

function clearSearchResults(): void {
  searchResults.value = []
}

function cancelSearch(): void {
  searchRequestSequence += 1
  if (activeSearchController) {
    activeSearchController.abort()
    activeSearchController = null
  }
  isSearching.value = false
}

function resetState(): void {
  savedLocation.value = null
  homeLocation.value = null
  currentLocation.value = null
  savedLocations.value = []
  clearSearchResults()
  clearError()
  resetWeatherData()
}

async function loadSavedLocation(): Promise<WeatherLocationPayload | null> {
  isLoadingLocation.value = true
  clearError()

  try {
    const response = await fetch('/api/user/weather/location', {
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response, 'Failed to load saved location'))
    }

    const payload = await response.json() as SavedLocationResponse
    savedLocation.value = payload.location
    homeLocation.value = payload.location

    const localSaved = readLocalSavedLocations()
    savedLocations.value = localSaved

    if (payload.location) {
      upsertSavedLocation(payload.location)
    }

    if (!currentLocation.value && homeLocation.value) {
      currentLocation.value = homeLocation.value
    }

    if (!currentLocation.value && savedLocations.value.length > 0) {
      currentLocation.value = savedLocations.value[0] ?? null
    }

    return payload.location
  } catch (error) {
    savedLocation.value = null
    homeLocation.value = null
    savedLocations.value = readLocalSavedLocations()
    currentLocation.value = savedLocations.value[0] ?? null
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load saved location'
    return null
  } finally {
    isLoadingLocation.value = false
  }
}

async function loadWeather(force = false): Promise<void> {
  isLoadingWeather.value = true
  clearError()

  try {
    const params = new URLSearchParams()
    if (force) {
      params.set('force', 'true')
    }

    const queryString = params.toString()
    const url = queryString ? `/api/user/weather?${queryString}` : '/api/user/weather'
    const response = await fetch(url, {
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response, 'Failed to load weather'))
    }

    const payload = await response.json() as WebsiteWeatherResponse
    savedLocation.value = payload.location
    if (payload.location) {
      homeLocation.value = payload.location
      upsertSavedLocation(payload.location)
      if (!currentLocation.value) {
        currentLocation.value = payload.location
      }
    }
    currentWeather.value = payload.current_weather
    forecastData.value = payload.forecast ?? []
    hourlyDaytimeData.value = payload.hourly_daytime ?? []
    hourlyNighttimeData.value = payload.hourly_nighttime ?? []
    cached.value = Boolean(payload.cached)

    // Extracted out of watcher to fix race conditions: send complete data to the Android widget immediately.
    await updateWidgetData(currentWeather.value, forecastData.value, currentLocation.value)
  } catch (error) {
    resetWeatherData()
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load weather'
  } finally {
    isLoadingWeather.value = false
  }
}

async function searchLocations(query: string, lang: AvailableLocale): Promise<WeatherLocationPayload[]> {
  const cleanedQuery = query.trim()
  if (cleanedQuery.length < 2) {
    cancelSearch()
    clearSearchResults()
    return []
  }

  cancelSearch()
  const requestId = ++searchRequestSequence
  const controller = new AbortController()
  activeSearchController = controller

  isSearching.value = true
  clearError()

  try {
    const params = new URLSearchParams({
      query: cleanedQuery,
      lang
    })

    const response = await fetch(`/api/user/weather/search?${params.toString()}`, {
      credentials: 'include',
      signal: controller.signal
    })

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response, 'Failed to search locations'))
    }

    const payload = await response.json() as LocationSearchResponse
    if (requestId !== searchRequestSequence) {
      return []
    }

    searchResults.value = payload.locations ?? []
    return searchResults.value
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return []
    }

    if (requestId !== searchRequestSequence) {
      return []
    }

    clearSearchResults()
    errorMessage.value = error instanceof Error ? error.message : 'Failed to search locations'
    return []
  } finally {
    if (requestId === searchRequestSequence) {
      isSearching.value = false
      activeSearchController = null
    }
  }
}

async function saveLocation(location: WeatherLocationPayload, setAsHome = true): Promise<WeatherLocationPayload | null> {
  isSavingLocation.value = true
  clearError()

  try {
    upsertSavedLocation(location)

    if (!setAsHome) {
      return location
    }

    const response = await fetch('/api/user/weather/location', {
      method: 'PUT',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(location)
    })

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response, 'Failed to save location'))
    }

    const payload = await response.json() as SavedLocationResponse
    savedLocation.value = payload.location
    homeLocation.value = payload.location
    if (payload.location) {
      upsertSavedLocation(payload.location)
      currentLocation.value = payload.location
    }
    clearSearchResults()
    return payload.location
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to save location'
    return null
  } finally {
    isSavingLocation.value = false
  }
}

async function deleteLocation(): Promise<boolean> {
  isSavingLocation.value = true
  clearError()

  try {
    const response = await fetch('/api/user/weather/location', {
      method: 'DELETE',
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response, 'Failed to delete location'))
    }

    savedLocation.value = null
    homeLocation.value = null
    if (currentLocation.value) {
      removeSavedLocationEntry(currentLocation.value)
    }
    clearSearchResults()
    resetWeatherData()
    return true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to delete location'
    return false
  } finally {
    isSavingLocation.value = false
  }
}

function setCurrentLocation(location: WeatherLocationPayload | null): void {
  currentLocation.value = location
}

async function setHomeLocation(location: WeatherLocationPayload): Promise<WeatherLocationPayload | null> {
  return saveLocation(location, true)
}

async function removeSavedLocation(location: WeatherLocationPayload): Promise<boolean> {
  removeSavedLocationEntry(location)

  if (homeLocation.value && getLocationKey(homeLocation.value) === getLocationKey(location)) {
    return deleteLocation()
  }

  if (currentLocation.value && getLocationKey(currentLocation.value) === getLocationKey(location)) {
    currentLocation.value = homeLocation.value ?? savedLocations.value[0] ?? null
    if (currentLocation.value) {
      await loadWeatherForLocation(currentLocation.value)
    } else {
      resetWeatherData()
    }
  }

  return true
}

async function loadWeatherForLocation(location: WeatherLocationPayload | null, force = false): Promise<void> {
  if (!location) {
    resetWeatherData()
    return
  }

  setCurrentLocation(location)
  
  isLoadingWeather.value = true
  clearError()

  try {
    const params = new URLSearchParams({
      latitude: location.latitude.toString(),
      longitude: location.longitude.toString(),
      name: location.name,
      country: location.country,
      state: location.state,
      county: location.county,
      country_code: location.country_code,
      altitude: location.altitude.toString()
    })
    if (force) {
      params.set('force', 'true')
    }

    const queryString = params.toString()
    const url = queryString ? `/api/user/weather/preview?${queryString}` : '/api/user/weather/preview'
    const response = await fetch(url, {
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response, 'Failed to load weather'))
    }

    const payload = await response.json() as WebsiteWeatherResponse
    currentWeather.value = payload.current_weather
    forecastData.value = payload.forecast ?? []
    hourlyDaytimeData.value = payload.hourly_daytime ?? []
    hourlyNighttimeData.value = payload.hourly_nighttime ?? []
    cached.value = Boolean(payload.cached)

    // Extracted out of watcher to fix race conditions: send complete data to the Android widget immediately.
    await updateWidgetData(currentWeather.value, forecastData.value, location)
  } catch (error) {
    resetWeatherData()
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load weather'
  } finally {
    isLoadingWeather.value = false
  }
}

// Explicitly updating data inside load functions now instead of detached watchers

function translateWeatherCondition(weather: { wid?: number, main?: string }): string {
  // Try wid first (Open Meteo code)
  if (weather.wid !== undefined) {
    const key = `weather_${weather.wid}`
    const translated = i18n.global.t(key)
    if (translated !== key) return translated
  }
  
  // Fall back to main string (lowercase for consistency)
  if (weather.main) {
    const key = `weather_${weather.main.toLowerCase()}`
    const translated = i18n.global.t(key)
    if (translated !== key) return translated
    
    // If no translation found, return the main string as is
    return weather.main
  }
  
  return ''
}

async function updateWidgetData(weather: any, forecast: any[], location: WeatherLocationPayload | null) {
  if (!weather) return

  try {
    const todayForecast = forecast?.[0]
    await Preferences.set({
      key: 'widget_weather_data',
      value: JSON.stringify({
        temp: Math.round(weather.temp),
        temp_min: todayForecast?.temp_min ? Math.round(todayForecast.temp_min) : Math.round(weather.temp),
        temp_max: todayForecast?.temp_max ? Math.round(todayForecast.temp_max) : Math.round(weather.temp),
        main: translateWeatherCondition(weather),
        icon: weather.icon,
        locationName: location?.name || 'Unknown Location',
        updateTime: new Date().getTime()
      })
    })
  } catch {
    // Ignore on web
  }
}

export function useWebsiteWeather() {
  const hasSavedLocation = computed(() => savedLocations.value.length > 0 || savedLocation.value !== null)
  const hasWeather = computed(() => currentWeather.value !== null)
  const isBusy = computed(() => {
    return isLoadingLocation.value || isLoadingWeather.value || isSearching.value || isSavingLocation.value
  })

  return {
    savedLocation,
    savedLocations,
    currentLocation,
    homeLocation,
    currentWeather,
    forecastData,
    hourlyDaytimeData,
    hourlyNighttimeData,
    searchResults,
    cached,
    errorMessage,
    isLoadingLocation,
    isLoadingWeather,
    isSearching,
    isSavingLocation,
    hasSavedLocation,
    hasWeather,
    isBusy,
    clearError,
    clearSearchResults,
    cancelSearch,
    resetState,
    loadSavedLocation,
    loadWeather,
    searchLocations,
    saveLocation,
    deleteLocation,
    removeSavedLocation,
    setHomeLocation,
    setCurrentLocation,
    loadWeatherForLocation
  }
}