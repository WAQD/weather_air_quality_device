<template>
  <div id="weather_container"
    class="container mx-auto px-2 sm:px-6 lg:px-8 py-2 sm:py-6 lg:py-8 max-w-full">
    <div id="weather_grid"
      class="flex flex-col xl:grid gap-3 sm:gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div class="contents xl:block xl:space-y-3 xl:sm:space-y-6">
        <CurrentWeatherCard :start-collapsed="isForecastDeepLink" />
      </div>
      <div class="contents xl:block xl:space-y-3 xl:sm:space-y-6">
        <LocationBanner />
        <ForecastPanel :initial-day-index="widgetForecastDay" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CurrentWeatherCard from '../components/CurrentWeatherCard.vue'
import ForecastPanel from '../components/ForecastPanel.vue'
import LocationBanner from '../components/LocationBanner.vue'
import { useTranslation } from '../composables/useTranslation'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'

const route = useRoute()
const router = useRouter()
const { locale } = useTranslation()
const {
  currentLocation,
  homeLocation,
  currentWeather,
  clearError,
  clearSuccess,
  clearSearchResults,
  loadSavedLocation,
  loadWeather,
  searchLocations,
  loadWeatherForLocation,
  getLocationKey
} = useWebsiteWeather()

const routeQuery = computed(() => {
  const query = route.query.q
  return typeof query === 'string' ? query : ''
})

function parseDayQuery(day: unknown): number | null {
  if (typeof day === 'string') {
    const parsed = parseInt(day, 10)
    if (!isNaN(parsed) && parsed >= 0) return parsed
  }
  return null
}

const widgetForecastDay = ref(parseDayQuery(route.query.day) ?? 0)

// True when this page was reached from the Android widget's forecast deep link
// (a valid ?day= param). On stacked layouts the current weather card collapses
// into a compact bar so the forecast is visible with little/no scrolling, which
// also avoids the previous scroll-overshoot caused by repeatedly scrolling to the
// forecast while the forecast content below was still rendering.
const isForecastDeepLink = ref(false)

function clearWidgetQueryParams() {
  const { day: _day, gps_lat: _gpsLat, gps_lon: _gpsLon, gps_name: _gpsName, ...rest } = route.query
  router.replace({ path: route.path, query: rest })
}

watch(routeQuery, async (query) => {
  clearSuccess()
  clearError()
  if (query.trim().length < 2) {
    clearSearchResults()
    return
  }
  await searchLocations(query, locale.value)
}, { immediate: true })

watch(locale, async () => {
  if (routeQuery.value.trim().length >= 2) {
    await searchLocations(routeQuery.value, locale.value)
  }
})

watch(() => route.fullPath, async (newPath, oldPath) => {
  if (oldPath && newPath !== oldPath && route.path === '/rest/weather') {
    const alreadyHasData = !!currentWeather.value
    const isWidgetTrigger = !!(route.query.gps_lat && route.query.gps_lon) || route.query.day !== undefined

    if (route.query.gps_lat && route.query.gps_lon) {
      const gpsLoc: WeatherLocationPayload = {
        name: String(route.query.gps_name || 'GPS Location'),
        country: '', state: '', county: '', country_code: '',
        altitude: 0,
        latitude: parseFloat(String(route.query.gps_lat)),
        longitude: parseFloat(String(route.query.gps_lon)),
      }
      await loadWeatherForLocation(gpsLoc)
    } else if (currentLocation.value && (!homeLocation.value || getLocationKey(homeLocation.value) !== getLocationKey(currentLocation.value))) {
      await loadWeatherForLocation(currentLocation.value, false, alreadyHasData)
    } else {
      await loadWeather(false, alreadyHasData)
    }

    if (isWidgetTrigger) {
      const parsedDay = parseDayQuery(route.query.day)
      if (parsedDay !== null) {
        widgetForecastDay.value = parsedDay
        isForecastDeepLink.value = true
      }
      clearWidgetQueryParams()
    }
  }
})

onMounted(async () => {
  const alreadyHasData = !!currentWeather.value
  await loadSavedLocation()
  const isWidgetTrigger = !!(route.query.gps_lat && route.query.gps_lon) || route.query.day !== undefined

  if (route.query.gps_lat && route.query.gps_lon) {
    const gpsLoc: WeatherLocationPayload = {
      name: String(route.query.gps_name || 'GPS Location'),
      country: '', state: '', county: '', country_code: '',
      altitude: 0,
      latitude: parseFloat(String(route.query.gps_lat)),
      longitude: parseFloat(String(route.query.gps_lon)),
    }
    await loadWeatherForLocation(gpsLoc)
  } else if (currentLocation.value && (!homeLocation.value || getLocationKey(homeLocation.value) !== getLocationKey(currentLocation.value))) {
    await loadWeatherForLocation(currentLocation.value, false, alreadyHasData)
  } else {
    await loadWeather(false, alreadyHasData)
  }

  if (isWidgetTrigger) {
    const parsedDay = parseDayQuery(route.query.day)
    if (parsedDay !== null) {
      widgetForecastDay.value = parsedDay
      isForecastDeepLink.value = true
    }
    clearWidgetQueryParams()
  }
})
</script>