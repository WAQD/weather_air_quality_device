import { computed, ref, watch } from 'vue'
import { Preferences } from '@capacitor/preferences'
import { Geolocation } from '@capacitor/geolocation'
import { NativeSettings, AndroidSettings } from 'capacitor-native-settings'
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
const LOCATION_MODE_KEY = 'waqd.website.locationMode'
const WIDGET_STYLE_KEY = 'waqd.website.widgetStyle'

export type LocationMode = 'home' | 'gps'
export type WidgetStyle = 'simple' | 'forecast'

const locationMode = ref<LocationMode>('home')
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
const isLoadingLocation = ref(false)
const isLoadingWeather = ref(false)
const isRefreshingWeather = ref(false)
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
    const [modeRes, styleRes] = await Promise.all([
      Preferences.get({ key: LOCATION_MODE_KEY }),
      Preferences.get({ key: WIDGET_STYLE_KEY })
    ])
    
    if (modeRes.value === 'gps' || modeRes.value === 'home') {
      locationMode.value = modeRes.value as LocationMode
    }
    
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
      // Merge backend list with local storage
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

    // Extracted out of watcher to fix race conditions: send complete data to the Android widget immediately.
    // Always use payload.location (home) — currentLocation may point to a browsed city.
    await updateWidgetData(currentWeather.value, forecastData.value, payload.location)
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
    
    // Always persist to the saved-locations list backend
    fetch('/api/user/weather/saved-locations', {
      method: 'PUT',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(location)
    }).catch(() => { /* silent fallback on backend failure */ })

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

async function setLocationMode(mode: LocationMode): Promise<void> {
  locationMode.value = mode
  await Preferences.set({ key: LOCATION_MODE_KEY, value: mode })
  if (mode === 'home' && homeLocation.value) {
    await loadWeatherForLocation(homeLocation.value, false, true)
  } else if (mode === 'gps') {
    await loadWeatherByGps()
  }
}

async function setWidgetStyle(style: WidgetStyle): Promise<void> {
  widgetStyle.value = style
  await Preferences.set({ key: WIDGET_STYLE_KEY, value: style })
  // Force update widget with current data, using home or GPS location — not the browsed location.
  if (currentWeather.value) {
    const widgetLocation = locationMode.value === 'home' ? homeLocation.value : currentLocation.value
    await updateWidgetData(currentWeather.value, forecastData.value, widgetLocation)
  }
}

async function loadWeatherByGps(): Promise<void> {
  isLoadingWeather.value = true
  clearError()
  console.log('GPS: Starting acquisition...')
  try {
    // Check/Request permissions first for better UX
    try {
      const perm = await Geolocation.checkPermissions()
      console.log('GPS: Permission status:', perm.location)
      if (perm.location !== 'granted') {
        console.log('GPS: Requesting permissions...')
        const req = await Geolocation.requestPermissions()
        console.log('GPS: Request result:', req.location)
        if (req.location !== 'granted') {
          console.log('GPS: Permission denied. Opening system settings...')
          await NativeSettings.open({
            option: AndroidSettings.ApplicationDetails
          })
          throw new Error('Location permission denied. Please enable in settings.')
        }
      }
    } catch (e) {
      console.warn('GPS: Permission check failed:', e)
    }

    console.log('GPS: Calling getCurrentPosition...')
    const coordinates = await Geolocation.getCurrentPosition({
      enableHighAccuracy: false,
      timeout: 10000,
      maximumAge: 60000
    })
    console.log('GPS: Received coordinates:', coordinates.coords.latitude, coordinates.coords.longitude)

    const params = new URLSearchParams({
      latitude: coordinates.coords.latitude.toString(),
      longitude: coordinates.coords.longitude.toString(),
      name: 'Selected location' // Trigger backend reverse geocoding
    })
    const url = `/api/user/weather/preview?${params.toString()}`
    console.log('GPS: Fetching weather from:', url)
    const response = await fetch(url, {
      credentials: 'include'
    })

    if (!response.ok) {
      console.error('GPS: Weather fetch failed status:', response.status)
      throw new Error('Failed to load GPS weather data')
    }

    const payload = await response.json() as WebsiteWeatherResponse
    console.log('GPS: Weather payload received for:', payload.location?.name)
    currentLocation.value = payload.location
    currentWeather.value = payload.current_weather
    forecastData.value = payload.forecast ?? []
    hourlyDaytimeData.value = payload.hourly_daytime ?? []
    hourlyNighttimeData.value = payload.hourly_nighttime ?? []
    cached.value = Boolean(payload.cached)

    await updateWidgetData(currentWeather.value, forecastData.value, payload.location)
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'GPS error'
    errorMessage.value = `GPS failed: ${msg}. Switching to Home.`
    console.error('GPS error:', error)
    
    // Fallback to Home mode on failure
    if (homeLocation.value) {
      locationMode.value = 'home'
      await Preferences.set({ key: LOCATION_MODE_KEY, value: 'home' })
      await loadWeatherForLocation(homeLocation.value)
    }
  } finally {
    isLoadingWeather.value = false
  }
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

  // Remove from backend list
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

async function loadWeatherForLocation(location: WeatherLocationPayload | null, force = false, updateWidget = false, silent = false): Promise<void> {
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
    currentWeather.value = payload.current_weather
    forecastData.value = payload.forecast ?? []
    hourlyDaytimeData.value = payload.hourly_daytime ?? []
    hourlyNighttimeData.value = payload.hourly_nighttime ?? []
    cached.value = Boolean(payload.cached)

    // Only update widget for home/GPS loads, not for search previews
    if (updateWidget) {
      await updateWidgetData(currentWeather.value, forecastData.value, location)
    }
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
    
    // Generate 3 day forecast array for Android Widget, starting from tomorrow (index 1 to 4)
    const forecast3Days = forecast?.slice(1, 4).map((day: any) => {
      // Get short day name (e.g. "Mon")
      const dateStr = day.date_time
      const dateObj = new Date(dateStr)
      // use standard formatter to get short day in the active locale
      const shortDay = new Intl.DateTimeFormat(i18n.global.locale.value, { weekday: 'short' }).format(dateObj)
      
      return {
        day: shortDay,
        icon: day.icon,
        temp_min: Math.round(day.temp_min),
        temp_max: Math.round(day.temp_max)
      }
    }) || []

    await Preferences.set({
      key: 'widget_weather_data',
      value: JSON.stringify({
        temp: Math.round(weather.temp),
        temp_min: todayForecast?.temp_min ? Math.round(todayForecast.temp_min) : Math.round(weather.temp),
        temp_max: todayForecast?.temp_max ? Math.round(todayForecast.temp_max) : Math.round(weather.temp),
        main: translateWeatherCondition(weather),
        icon: weather.icon,
        locationName: location?.name || 'Unknown Location',
        updateTime: new Date().getTime(),
        widget_style: widgetStyle.value,
        forecast_3_days: forecast3Days
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
    isRefreshingWeather,
    isSearching,
    isSavingLocation,
    hasSavedLocation,
    hasWeather,
    isBusy,
    locationMode,
    widgetStyle,
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
    setLocationMode,
    setWidgetStyle,
    loadWeatherByGps,
    setCurrentLocation,
    loadWeatherForLocation
  }
}