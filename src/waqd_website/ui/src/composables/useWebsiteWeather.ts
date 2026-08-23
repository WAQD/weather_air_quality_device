import { computed, ref } from 'vue'
import { Preferences } from '@capacitor/preferences'
import { Geolocation } from '@capacitor/geolocation'
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
const WIDGET_STYLE_KEY = 'waqd.website.widgetStyle'

export type WidgetStyle = 'simple' | 'forecast'

const widgetStyle = ref<WidgetStyle>('simple')
const savedLocation = ref<WeatherLocationPayload | null>(null)
const savedLocations = ref<WeatherLocationPayload[]>([])
const currentLocation = ref<WeatherLocationPayload | null>(null)
const homeLocation = ref<WeatherLocationPayload | null>(null)
const currentWeather = ref<WeatherData | null>(null)
const forecastData = ref<ForecastData[]>([])
const hourlyDaytimeData = ref<HourlyWeatherData[][]>([])
const hourlyNighttimeData = ref<HourlyWeatherData[][]>([])
const searchResults = ref<WeatherLocationPayload[]>([])
const deviceLocation = ref<WeatherLocationPayload | null>(null)
const isLoadingDeviceLocation = ref(false)
const isResolvingDeviceLocation = ref(false)
const isLoadingLocation = ref(false)
const isLoadingWeather = ref(false)
const isRefreshingWeather = ref(false)
const isSearching = ref(false)
const isSavingLocation = ref(false)
const cached = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
let activeSearchController: AbortController | null = null
let searchRequestSequence = 0

export function getLocationKey(location: WeatherLocationPayload): string {
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

function clearSuccess(): void {
  successMessage.value = ''
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
  deviceLocation.value = null
  savedLocations.value = []
  clearSearchResults()
  clearError()
  resetWeatherData()
}

async function loadDeviceLocation(): Promise<WeatherLocationPayload | null> {
  if (isLoadingDeviceLocation.value) {
    return deviceLocation.value
  }
  isLoadingDeviceLocation.value = true

  try {
    const position = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 30000,
    })

    const location: WeatherLocationPayload = {
      name: '',
      country: '',
      state: '',
      county: '',
      country_code: '',
      altitude: position.coords.altitude ?? 0,
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    }
    deviceLocation.value = location
    return location
  } catch (error) {
    deviceLocation.value = null
    console.warn('Could not determine device location:', error)
    return null
  } finally {
    isLoadingDeviceLocation.value = false
  }
}

async function resolveDeviceLocation(): Promise<WeatherLocationPayload | null> {
  if (isResolvingDeviceLocation.value) {
    return deviceLocation.value
  }
  isResolvingDeviceLocation.value = true

  try {
    let location = deviceLocation.value
    if (!location) {
      location = await loadDeviceLocation()
    }
    if (!location) {
      return null
    }
    // Already resolved (has a name); no need to reverse-geocode again
    if (location.name) {
      return location
    }

    const params = new URLSearchParams({
      latitude: location.latitude.toString(),
      longitude: location.longitude.toString(),
    })

    const response = await fetch(`/api/user/weather/reverse-geocode?${params.toString()}`, {
      credentials: 'include',
    })

    if (!response.ok) {
      return location
    }

    const payload = await response.json() as SavedLocationResponse
    if (payload.location) {
      deviceLocation.value = payload.location
      return payload.location
    }

    return location
  } catch {
    return deviceLocation.value
  } finally {
    isResolvingDeviceLocation.value = false
  }
}

async function loadSavedLocation(): Promise<WeatherLocationPayload | null> {
  isLoadingLocation.value = true
  clearError()

  try {
    const [styleRes] = await Promise.all([
      Preferences.get({ key: WIDGET_STYLE_KEY })
    ])

    if (styleRes.value === 'simple' || styleRes.value === 'forecast') {
      widgetStyle.value = styleRes.value as WidgetStyle
    }

    const [response, savedResponse] = await Promise.all([
      fetch('/api/user/weather/location', { credentials: 'include' }),
      fetch('/api/user/weather/saved-locations', { credentials: 'include' })
    ])

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response, 'Failed to load saved location'))
    }
    if (!savedResponse.ok) {
      throw new Error(await extractErrorMessage(savedResponse, 'Failed to load saved locations list'))
    }

    const payload = await response.json() as SavedLocationResponse
    const savedPayload = await savedResponse.json() as LocationSearchResponse

    savedLocation.value = payload.location
    homeLocation.value = payload.location

    let localSaved = readLocalSavedLocations()
    if (savedPayload.locations && savedPayload.locations.length > 0) {
      savedPayload.locations.forEach(loc => upsertSavedLocation(loc))
      localSaved = readLocalSavedLocations()
    }

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

async function loadWeather(force = false, silent = false): Promise<void> {
  if (silent) {
    isRefreshingWeather.value = true
  } else {
    isLoadingWeather.value = true
  }
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

    // Widget is GPS-only now; don't write home data to widget
  } catch (error) {
    if (!silent) {
      resetWeatherData()
    }
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load weather'
  } finally {
    if (silent) {
      isRefreshingWeather.value = false
    } else {
      isLoadingWeather.value = false
    }
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

    fetch('/api/user/weather/saved-locations', {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(location)
    }).catch(() => { /* silent fallback */ })

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

async function setWidgetStyle(style: WidgetStyle): Promise<void> {
  widgetStyle.value = style
  await Preferences.set({ key: WIDGET_STYLE_KEY, value: style })
  // Widget is GPS-only; style is applied by the native worker, not by writing home data here
}

async function setHomeLocation(location: WeatherLocationPayload): Promise<WeatherLocationPayload | null> {
  const result = await saveLocation(location, true)
  if (result) {
    setCurrentLocation(result)
  }
  return result
}

async function removeSavedLocation(location: WeatherLocationPayload): Promise<boolean> {
  removeSavedLocationEntry(location)

  fetch(`/api/user/weather/saved-locations?latitude=${location.latitude}&longitude=${location.longitude}`, {
    method: 'DELETE',
    credentials: 'include'
  }).catch(() => { /* silent fallback */ })

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

async function loadWeatherForLocation(location: WeatherLocationPayload | null, force = false, silent = false): Promise<void> {
  if (!location) {
    resetWeatherData()
    return
  }

  setCurrentLocation(location)

  if (silent) {
    isRefreshingWeather.value = true
  } else {
    isLoadingWeather.value = true
  }
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
    if (payload.location) {
      currentLocation.value = payload.location
    }
    currentWeather.value = payload.current_weather
    forecastData.value = payload.forecast ?? []
    hourlyDaytimeData.value = payload.hourly_daytime ?? []
    hourlyNighttimeData.value = payload.hourly_nighttime ?? []
    cached.value = Boolean(payload.cached)
  } catch (error) {
    if (!silent) {
      resetWeatherData()
    }
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load weather'
  } finally {
    if (silent) {
      isRefreshingWeather.value = false
    } else {
      isLoadingWeather.value = false
    }
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
    deviceLocation,
    cached,
    errorMessage,
    successMessage,
    isLoadingDeviceLocation,
    isResolvingDeviceLocation,
    isLoadingLocation,
    isLoadingWeather,
    isRefreshingWeather,
    isSearching,
    isSavingLocation,
    hasSavedLocation,
    hasWeather,
    isBusy,
    widgetStyle,
    clearError,
    clearSuccess,
    clearSearchResults,
    cancelSearch,
    resetState,
    loadSavedLocation,
    loadDeviceLocation,
    resolveDeviceLocation,
    loadWeather,
    searchLocations,
    saveLocation,
    deleteLocation,
    removeSavedLocation,
    setHomeLocation,
    setWidgetStyle,
    setCurrentLocation,
    loadWeatherForLocation,
    getLocationKey
  }
}
