<template>
  <div id="current_weather_card"
    class="order-2 xl:order-none card bg-base-100 shadow-xl overflow-hidden"
    :style="weatherHeroStyle">
    <!-- Compact collapsed summary: used only for widget/forecast deep links on stacked
         (mobile/tablet) layouts so the forecast below needs little or no scrolling.
         Tapping expands back to the full card. -->
    <button v-if="showCompact" id="current_weather_compact" type="button"
      class="card-body w-full cursor-pointer p-3 sm:p-4 text-left backdrop-blur-md focus:outline-none"
      :class="weatherTintClass" aria-expanded="false" @click="expanded = true">
      <div class="flex items-center gap-3">
        <template v-if="currentWeather">
          <img v-if="currentWeather.icon" :src="`/static/weather_icons/${currentWeather.icon}.svg`"
            :alt="currentWeather.main"
            class="h-10 w-10 shrink-0 brightness-0 invert-0 weather-icon" />
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-semibold opacity-80">{{ currentLocation ?
              formatLocationLabel(currentLocation) : t('no_location') }}</p>
            <p class="text-2xl font-bold leading-tight">
              {{ currentWeather.temp.toFixed(1) }}°C
              <span class="text-sm font-normal opacity-70">{{
                translateWeatherCondition(currentWeather) }}</span>
            </p>
            <p v-if="currentWeather.apparent_temperature !== undefined" class="text-xs opacity-70">
              {{ t('feels_like') }}: {{ currentWeather.apparent_temperature.toFixed(1) }}°C
            </p>
          </div>
        </template>
        <template v-else-if="isLoadingWeather">
          <span class="loading loading-spinner loading-sm shrink-0"></span>
          <p class="min-w-0 flex-1 truncate text-sm opacity-80">{{ currentLocation ?
            formatLocationLabel(currentLocation) : t('no_location') }}</p>
        </template>
        <template v-else>
          <p class="min-w-0 flex-1 text-sm opacity-70">{{ t('home_weather_needs_location')
          }}</p>
        </template>
        <svg class="h-6 w-6 shrink-0 text-base-content/50" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          aria-hidden="true">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>
    </button>

    <!-- Expanded full card (also the normal view when not collapsed) -->
    <div v-else class="card-body p-3 sm:p-6 backdrop-blur-md" :class="weatherTintClass">
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.22em] opacity-60">
            {{ t('current_weather') }}</p>
          <h1 class="mt-2 text-2xl sm:text-3xl font-bold">{{ t('home_weather') }}</h1>
        </div>
        <button v-if="collapseEnabled" id="current_weather_collapse" type="button"
          class="btn btn-ghost btn-sm btn-circle shrink-0" :aria-label="t('home_weather')"
          @click="expanded = false">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 15l-6-6-6 6" />
          </svg>
        </button>
      </div>

      <div v-if="isLoadingWeather" class="mt-5">
        <div class="rounded-box border border-base-300 bg-base-200/70 p-4">
          <div class="flex items-center gap-3 text-sm sm:text-base">
            <span class="loading loading-spinner loading-sm"></span>
            <span>Loading weather data...</span>
          </div>
        </div>
      </div>

      <div v-else-if="currentWeather" class="mt-5 space-y-4">
        <div class="flex items-center gap-4">
          <img v-if="currentWeather.icon" :src="`/static/weather_icons/${currentWeather.icon}.svg`"
            :alt="currentWeather.main" class="h-16 w-16 brightness-0 invert-0 weather-icon" />
          <div>
            <p class="text-4xl font-bold">{{ currentWeather.temp.toFixed(1) }}°C</p>
            <p class="text-sm sm:text-base opacity-75">{{
              translateWeatherCondition(currentWeather) }}</p>
            <p v-if="currentWeather.apparent_temperature !== undefined"
              class="text-sm sm:text-base opacity-75">
              {{ t('feels_like') }}: {{ currentWeather.apparent_temperature.toFixed(1) }}°C
            </p>
          </div>
        </div>

        <div>
          <p class="font-semibold text-base">{{ currentLocation ?
            formatLocationLabel(currentLocation) : t('no_location') }}</p>
          <p class="text-sm opacity-70 flex items-center gap-1.5">
            {{ t('last_updated') }}: {{ currentWeatherUpdatedAt }}
            <span v-if="isRefreshingWeather" class="loading loading-spinner"
              style="width: 0.9em; height: 0.9em;"></span>
          </p>
        </div>

        <WeatherMetric icon-class="text-base-content/50" :label="t('weather_clouds')"
          :value="`${currentWeather.clouds.toFixed(0)}%`" :icon-url="cloudsIconUrl" />

        <div class="grid grid-cols-1 gap-3 text-sm">
          <WeatherMetric icon-class="text-info" :label="t('humidity')"
            :value="`${currentWeather.humidity.toFixed(0)}%`" :icon-url="raindropIconUrl" />
          <WeatherMetric icon-class="text-accent" :label="t('wind')"
            :value="`${(currentWeather.wind_speed * 3.6).toFixed(1)} km/h`"
            :icon-url="windDegIconUrl" :rotate="((currentWeather.wind_deg ?? 0) + 180) % 360" />
          <WeatherMetric icon-class="text-secondary" :label="t('pressure')"
            :value="`${currentWeather.pressure.toFixed(0)} hPa`" :icon-url="pressureIconUrl" />
          <WeatherMetric icon-class="text-warning" :label="t('sunrise')"
            :value="formatTimeString(currentWeather.sunrise)" :icon-url="sunriseIconUrl" />
          <WeatherMetric icon-class="text-orange-400" :label="t('sunset')"
            :value="formatTimeString(currentWeather.sunset)" :icon-url="sunsetIconUrl" />
          <WeatherMetric icon-class="text-base-content/50" :label="t('elevation')"
            :value="currentWeather.altitude ? `${Math.round(currentWeather.altitude)} m` : '-'"
            :icon-url="altitudeIconUrl" />
        </div>
      </div>

      <div v-else
        class="mt-5 rounded-box border border-dashed border-base-300 bg-base-200/60 p-4 text-sm opacity-80">
        {{ t('home_weather_needs_location') }}
      </div>

      <div v-if="successMessage" class="alert alert-success mt-4 py-3 text-sm">
        <span>{{ successMessage }}</span>
      </div>
      <div v-if="errorMessage" class="alert alert-error mt-4 py-3 text-sm">
        <span>{{ errorMessage }}</span>
      </div>

      <div class="mt-5 flex flex-col gap-3">
        <button v-if="!isCurrentLocationSaved" class="btn btn-primary" type="button"
          :disabled="isSavingLocation || !currentLocation" @click="saveCurrentLocation">
          {{ t('save') }}
        </button>
        <button v-else class="btn btn-outline" type="button" :disabled="isSavingLocation"
          @click="setAsHome(currentLocation)">
          {{ t('set_home') }}
        </button>
        <button class="btn btn-secondary" type="button"
          :disabled="isLoadingWeather || !currentLocation" @click="refreshWeather(true)">
          {{ t('home_weather_refresh') }}
        </button>
        <button class="btn btn-ghost" type="button" :disabled="isSavingLocation || !homeLocation"
          @click="removeHomeLocation">
          {{ t('delete') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import { useWeather } from '../composables/useWeather'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'
import { formatLocationLabel } from '../utils/weather'
import WeatherMetric from './WeatherMetric.vue'

const WEATHER_VIEW_KEY = 'website-weather-view'

// When true, on stacked (mobile/tablet) layouts the card starts collapsed into a
// compact summary bar so the forecast below is reachable with little/no scrolling.
// The user can expand it back. This is only set for widget/forecast deep links.
const props = withDefaults(defineProps<{ startCollapsed?: boolean }>(), {
  startCollapsed: false
})
const expanded = ref(false)
const isDesktop = ref(false)

let desktopMedia: MediaQueryList | null = null
function onDesktopChange(e: MediaQueryListEvent): void {
  isDesktop.value = e.matches
}

// The xl breakpoint (1280px) is where the Weather view switches to its 2-column grid
// showing current weather + forecast side by side, so collapsing is unnecessary.
const collapseEnabled = computed(() => props.startCollapsed && !isDesktop.value)
const showCompact = computed(() => collapseEnabled.value && !expanded.value)

onMounted(() => {
  desktopMedia = window.matchMedia('(min-width: 1280px)')
  isDesktop.value = desktopMedia.matches
  desktopMedia.addEventListener('change', onDesktopChange)
})
onUnmounted(() => {
  desktopMedia?.removeEventListener('change', onDesktopChange)
})

const { t, locale } = useTranslation()
const { getWeatherBackground } = useWeather()
const {
  currentLocation,
  homeLocation,
  currentWeather,
  cached,
  savedLocations,
  isLoadingWeather,
  isRefreshingWeather,
  isSavingLocation,
  successMessage,
  errorMessage,
  clearSuccess,
  clearError,
  loadWeather,
  loadWeatherForLocation,
  saveLocation,
  setHomeLocation,
  deleteLocation,
  getLocationKey
} = useWebsiteWeather()

const raindropIconUrl = '/static/weather_icons/wi-raindrops.svg#Layer_1'
const windDegIconUrl = '/static/weather_icons/wi-wind-deg.svg#Layer_1'
const sunriseIconUrl = '/static/weather_icons/wi-sunrise.svg#Layer_1'
const sunsetIconUrl = '/static/weather_icons/wi-sunset.svg#Layer_1'
const altitudeIconUrl = '/static/general_icons/altitude.svg#main'
const pressureIconUrl = '/static/weather_icons/wi-barometer.svg#Layer_1'
const cloudsIconUrl = '/static/weather_icons/wi-cloudy.svg#Layer_1'

const weatherHeroStyle = computed(() => {
  if (!currentWeather.value) {
    return {}
  }

  return getWeatherBackground(WEATHER_VIEW_KEY)
})

const weatherTintClass = computed(() => {
  const main = currentWeather.value?.main?.toLowerCase() ?? ''
  switch (main) {
    case 'clear':
      return 'bg-warning/10'
    case 'rain':
    case 'drizzle':
    case 'squall':
      return 'bg-info/10'
    case 'thunderstorm':
      return 'bg-secondary/10'
    case 'snow':
      return 'bg-info/5'
    default:
      return 'bg-base-100/82'
  }
})

const currentWeatherUpdatedAt = computed(() => {
  if (!currentWeather.value?.fetch_time) {
    return '—'
  }

  return new Date(currentWeather.value.fetch_time).toLocaleString(locale.value)
})

async function refreshWeather(force = false): Promise<void> {
  clearSuccess()
  clearError()

  if (!currentLocation.value) {
    return
  }

  if (homeLocation.value && getLocationKey(homeLocation.value) === getLocationKey(currentLocation.value)) {
    await loadWeather(force)
    return
  }

  await loadWeatherForLocation(currentLocation.value, force)
}

async function removeHomeLocation(): Promise<void> {
  clearSuccess()
  clearError()
  const deleted = await deleteLocation()
  if (!deleted) {
    return
  }

  successMessage.value = t('home_weather_removed')
}

const isCurrentLocationSaved = computed(() => {
  if (!currentLocation.value) {
    return false
  }

  return savedLocations.value.some((loc) => getLocationKey(loc) === getLocationKey(currentLocation.value as WeatherLocationPayload))
})

async function saveCurrentLocation(): Promise<void> {
  if (!currentLocation.value) {
    return
  }

  clearSuccess()
  clearError()
  const saved = await saveLocation(currentLocation.value, false)
  if (!saved) {
    return
  }

  successMessage.value = t('home_weather_saved')
}

async function setAsHome(location: WeatherLocationPayload): Promise<void> {
  clearSuccess()
  clearError()
  const saved = await setHomeLocation(location)
  if (!saved) {
    return
  }

  successMessage.value = t('saved_as_home')
}

function translateWeatherCondition(weather: { wid?: number, main?: string }): string {
  if (weather.wid !== undefined) {
    const key = `weather_${weather.wid}`
    const translated = t(key)
    if (translated !== key) {
      return translated
    }
  }

  if (weather.main) {
    const key = `weather_${weather.main.toLowerCase()}`
    const translated = t(key)
    if (translated !== key) {
      return translated
    }

    return weather.main
  }

  return ''
}

function formatTimeString(timeStr: string): string {
  const parsed = new Date(timeStr)
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  const parts = (timeStr || '').split(':').map(Number)
  const date = new Date()
  date.setHours(parts[0] || 0, parts[1] || 0, parts[2] || 0, 0)
  return date.toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit', hour12: false })
}
</script>
