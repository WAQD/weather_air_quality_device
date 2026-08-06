<template>
    <div id="weather_container"
        class="container mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8 max-w-full">
        <div id="weather_grid"
            class="flex flex-col xl:grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
            <div class="contents xl:block xl:row-span-2 xl:space-y-6">
                <div id="current_weather_card"
                    class="order-2 xl:order-none card bg-base-100 shadow-xl overflow-hidden"
                    :style="weatherHeroStyle">
                    <div class="card-body p-5 sm:p-6 bg-base-100/82 backdrop-blur-md">
                        <div class="flex items-start justify-between gap-3">
                            <div>
                                <p
                                    class="text-xs font-semibold uppercase tracking-[0.22em] opacity-60">
                                    {{ t('current_weather') }}</p>
                                <h1 class="mt-2 text-2xl sm:text-3xl font-bold">{{
                                    t('home_weather') }}</h1>
                            </div>
                            <span v-if="cached && currentWeather"
                                class="badge badge-info badge-outline">{{
                                    t('home_weather_cached') }}</span>
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
                                <img v-if="currentWeather.icon"
                                    :src="`/static/weather_icons/${currentWeather.icon}.svg`"
                                    :alt="currentWeather.main"
                                    class="h-16 w-16 brightness-0 invert-0 weather-icon" />
                                <div>
                                    <p class="text-4xl font-bold">{{
                                        currentWeather.temp.toFixed(1) }}°C</p>
                                    <p class="text-sm sm:text-base opacity-75">{{
                                        translateWeatherCondition(currentWeather) }}</p>
                                </div>
                            </div>

                            <div>
                                <p class="font-semibold text-base">{{ currentLocation ?
                                    formatLocationLabel(currentLocation) : t('no_location') }}
                                </p>
                                <p class="text-sm opacity-70 flex items-center gap-1.5">
                                    {{ t('last_updated') }}: {{ currentWeatherUpdatedAt }}
                                    <span v-if="isRefreshingWeather" class="loading loading-spinner"
                                        style="width: 0.9em; height: 0.9em;"></span>
                                </p>
                            </div>
                            <div class="rounded-box bg-base-200/80 p-3">
                                <div class="flex items-center gap-3">
                                    <svg class="h-6 w-6 flex-none" aria-hidden="true">
                                        <use :href="cloudsIconUrl" fill="currentColor" />
                                    </svg>
                                    <div class="min-w-0">
                                        <p
                                            class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
                                            {{ t('weather_clouds') }}</p>
                                        <p class="mt-1 text-lg font-semibold">{{
                                            currentWeather.clouds.toFixed(0) }}%</p>
                                    </div>
                                </div>
                            </div>
                            <div class="grid grid-cols-1 gap-3 text-sm">
                                <div class="rounded-box bg-base-200/80 p-3">
                                    <div class="flex items-center gap-3">
                                        <svg class="h-6 w-6 flex-none" aria-hidden="true">
                                            <use :href="raindropIconUrl" fill="currentColor" />
                                        </svg>
                                        <div class="min-w-0">
                                            <p
                                                class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
                                                {{ t('humidity') }}</p>
                                            <p class="mt-1 text-lg font-semibold">{{
                                                currentWeather.humidity.toFixed(0) }}%</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="rounded-box bg-base-200/80 p-3">
                                    <div class="flex items-center gap-3">
                                        <svg class="h-6 w-6 weather-icon flex-none"
                                            aria-hidden="true"
                                            :style="{ transform: `rotate(${((currentWeather.wind_deg ?? 0) + 180) % 360}deg)`, transformOrigin: 'center' }">
                                            <use :href="windDegIconUrl" fill="currentColor" />
                                        </svg>
                                        <div class="min-w-0">
                                            <p
                                                class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
                                                {{ t('wind') }}</p>
                                            <p class="mt-1 text-lg font-semibold">{{
                                                (currentWeather.wind_speed * 3.6).toFixed(1) }}
                                                km/h</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="rounded-box bg-base-200/80 p-3">
                                    <div class="flex items-center gap-3">
                                        <svg class="h-6 w-6 flex-none" aria-hidden="true">
                                            <use :href="pressureIconUrl" fill="currentColor" />
                                        </svg>
                                        <div class="min-w-0">
                                            <p
                                                class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
                                                {{ t('pressure') }}</p>
                                            <p class="mt-1 text-lg font-semibold">{{
                                                currentWeather.pressure.toFixed(0) }} hPa</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="rounded-box bg-base-200/80 p-3">
                                    <div class="flex items-center gap-3">
                                        <svg class="h-6 w-6 weather-icon flex-none"
                                            aria-hidden="true">
                                            <use :href="sunriseIconUrl" fill="currentColor" />
                                        </svg>
                                        <div class="min-w-0">
                                            <p
                                                class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
                                                {{ t('sunrise') }}</p>
                                            <p class="mt-1 text-lg font-semibold">{{
                                                formatTimeString(currentWeather.sunrise) }}</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="rounded-box bg-base-200/80 p-3">
                                    <div class="flex items-center gap-3">
                                        <svg class="h-6 w-6 weather-icon flex-none"
                                            aria-hidden="true">
                                            <use :href="sunsetIconUrl" fill="currentColor" />
                                        </svg>
                                        <div class="min-w-0">
                                            <p
                                                class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
                                                {{ t('sunset') }}</p>
                                            <p class="mt-1 text-lg font-semibold">{{
                                                formatTimeString(currentWeather.sunset) }}</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="rounded-box bg-base-200/80 p-3">
                                    <div class="flex items-center gap-3">
                                        <svg class="h-6 w-6 weather-icon flex-none"
                                            aria-hidden="true">
                                            <use :href="altitudeIconUrl" fill="currentColor" />
                                        </svg>
                                        <div class="min-w-0">
                                            <p
                                                class="text-xs uppercase tracking-[0.16em] opacity-60 break-words whitespace-normal">
                                                {{ t('elevation') }}</p>
                                            <p class="mt-1 text-lg font-semibold">{{
                                                currentWeather.altitude ?
                                                    `${Math.round(currentWeather.altitude)} m` : '-'
                                            }}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div v-else
                            class="mt-5 rounded-box border border-dashed border-base-300 bg-base-200/60 p-4 text-sm opacity-80">
                            {{ t('home_weather_needs_location') }}
                        </div>

                        <div class="mt-5 flex flex-col gap-3">
                            <button class="btn btn-secondary" type="button"
                                :disabled="isLoadingWeather || !currentLocation"
                                @click="refreshWeather(true)">
                                {{ t('home_weather_refresh') }}
                            </button>
                            <button class="btn btn-ghost" type="button"
                                :disabled="isSavingLocation || !homeLocation"
                                @click="removeHomeLocation">
                                {{ t('delete') }}
                            </button>
                        </div>
                    </div>
                </div>

                <div id="saved_locations" class="order-4 xl:order-none card bg-base-100 shadow-xl">
                    <div class="card-body p-5 sm:p-6">
                        <div class="flex items-start justify-between gap-3">
                            <div>
                                <h2 class="card-title text-base sm:text-lg">{{
                                    t('home_weather_saved_location') }}</h2>
                                <p class="mt-1 text-sm opacity-70">{{ t('home_weather_search_help')
                                }}</p>
                            </div>
                        </div>

                        <div v-if="successMessage" class="alert alert-success mt-4 py-3 text-sm">
                            <span>{{ successMessage }}</span>
                        </div>
                        <div v-if="errorMessage" class="alert alert-error mt-4 py-3 text-sm">
                            <span>{{ errorMessage }}</span>
                        </div>

                        <div v-if="currentLocation" class="mt-4 flex flex-col gap-2">
                            <button v-if="!isCurrentLocationSaved" class="btn btn-primary"
                                type="button" :disabled="isSavingLocation"
                                @click="saveCurrentLocation">
                                {{ t('save') }}
                            </button>
                            <button v-if="isCurrentLocationSaved" class="btn btn-outline"
                                type="button" :disabled="isSavingLocation"
                                @click="setAsHome(currentLocation)">
                                {{ t('set_home') }}
                            </button>
                        </div>

                        <div v-if="savedLocations.length > 0" class="mt-5 space-y-2">
                            <p class="text-xs font-semibold uppercase tracking-[0.16em] opacity-60">
                                {{ t('saved_locations') }}</p>
                            <div v-for="location in savedLocations" :key="getLocationKey(location)"
                                class="rounded-box border border-base-300 bg-base-200/70 p-3">
                                <div class="min-w-0">
                                    <p class="font-semibold truncate break-words">{{ location.name
                                    }}</p>
                                </div>

                                <div class="mt-2 flex flex-col gap-2">
                                    <div class="text-xs opacity-70">{{ location.state ||
                                        location.country }}</div>
                                    <div class="flex flex-wrap gap-2">
                                        <button class="btn btn-xs" type="button"
                                            @click="selectLocation(location)">{{ t('open')
                                            }}</button>
                                        <button class="btn btn-xs btn-outline" type="button"
                                            :disabled="isSavingLocation"
                                            @click="setAsHome(location)">{{
                                                t('set_home')
                                            }}</button>
                                        <button class="btn btn-xs btn-ghost" type="button"
                                            :disabled="isSavingLocation"
                                            @click="removeSavedLocation(location)">{{ t('delete')
                                            }}</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Location banner: first on mobile (order-1), top of right column on desktop -->
            <div v-if="currentLocation" id="current_location_banner"
                class="order-1 xl:col-start-2 rounded-box border border-base-300 bg-base-200/70 p-4">
                <div class="flex items-start gap-3">
                    <div
                        class="text-2xl font-thin  tabular-nums hidden sm:block min-w-10 text-center">
                        {{ currentLocation.country_code }}
                    </div>
                    <div>
                        <img class="size-8 rounded-box p-1 bg-base-100"
                            :src="getFlagIconUrl(currentLocation.country_code)"
                            :alt="currentLocation.country_code" />
                    </div>
                    <div class="flex-1 min-w-0 flex items-start justify-between gap-3">
                        <div class="min-w-0">
                            <div class="text-2xl font-thin whitespace-nowrap">
                                {{ currentLocation.name }}</div>
                        </div>
                        <div class="shrink-0 text-right max-w-[11rem] sm:max-w-[16rem]">
                            <div class="text-xs uppercase font-semibold opacity-60 truncate">
                                {{ currentLocation.state || currentLocation.county ||
                                    currentLocation.country }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else id="no_location_banner"
                class="order-1 xl:col-start-2 rounded-box border border-dashed border-base-300 bg-base-200/60 p-4 text-sm opacity-80">
                {{ t('home_weather_needs_location') }}
            </div>

            <div id="forecast_container"
                class="order-3 xl:col-start-2 flex flex-col xl:block xl:min-w-0 xl:space-y-6">
                <div v-if="isLoadingWeather" id="forecast_loading"
                    class="card bg-base-100 shadow-xl">
                    <div class="card-body p-4 sm:p-6">
                        <div class="flex items-center gap-3 text-sm sm:text-base">
                            <span class="loading loading-spinner loading-md"></span>
                            <span>Loading forecast...</span>
                        </div>
                    </div>
                </div>
                <WeatherForecast v-else class="w-full"
                    :title="t('home_weather_forecast_title')" :forecast-data="forecastData"
                    :daytime-hourly-data="hourlyDaytimeData"
                    :nighttime-hourly-data="hourlyNighttimeData"
                    :initial-day-index="widgetForecastDay" />

                <!-- Map Container -->
                <div v-if="currentLocation"
                    class="card bg-base-100 shadow-xl overflow-hidden w-full">
                    <div class="card-body p-0">
                        <iframe width="100%" height="400" frameborder="0" scrolling="no"
                            marginheight="0" marginwidth="0" :src="osmEmbedUrl" style="border: 0;">
                        </iframe>
                        <div class="text-xs p-2 text-center opacity-70">
                            <a :href="`https://www.openstreetmap.org/?mlat=${currentLocation.latitude}&mlon=${currentLocation.longitude}#map=12/${currentLocation.latitude}/${currentLocation.longitude}`"
                                target="_blank" class="hover:underline">
                                View Larger Map on OpenStreetMap
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import WeatherForecast from '../components/WeatherForecast.vue'
import { useTranslation } from '../composables/useTranslation'
import { useWeather } from '../composables/useWeather'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'

const WEATHER_VIEW_KEY = 'website-weather-view'

const route = useRoute()
const { t, locale } = useTranslation()
const raindropIconUrl = '/static/weather_icons/wi-raindrops.svg#Layer_1'
const windDegIconUrl = '/static/weather_icons/wi-wind-deg.svg#Layer_1'
const sunriseIconUrl = '/static/weather_icons/wi-sunrise.svg#Layer_1'
const sunsetIconUrl = '/static/weather_icons/wi-sunset.svg#Layer_1'
const altitudeIconUrl = '/static/general_icons/altitude.svg#main'
const pressureIconUrl = '/static/weather_icons/wi-barometer.svg#Layer_1'
const cloudsIconUrl = '/static/weather_icons/wi-cloudy.svg#Layer_1'
// img-safe URLs (no fragment) for external <img> usage
// (no img-only fallbacks; use SVG <use> fragments)
const { setWeatherData, clearWeatherData, getWeatherBackground } = useWeather()
const {
    currentLocation,
    savedLocations,
    homeLocation,
    currentWeather,
    forecastData,
    hourlyDaytimeData,
    hourlyNighttimeData,
    searchResults,
    cached,
    errorMessage,
    isLoadingWeather,
    isRefreshingWeather,
    isSearching,
    isSavingLocation,
    clearError,
    clearSearchResults,
    loadSavedLocation,
    loadWeather,
    searchLocations,
    saveLocation,
    deleteLocation,
    removeSavedLocation: removeSavedLocationEntry,
    setHomeLocation,
    setCurrentLocation,
    loadWeatherForLocation
} = useWebsiteWeather()

const routeQuery = computed(() => {
    const query = route.query.q
    return typeof query === 'string' ? query : ''
})

const widgetForecastDay = computed(() => {
    const day = route.query.day
    if (typeof day === 'string') {
        const parsed = parseInt(day, 10)
        if (!isNaN(parsed) && parsed >= 0) return parsed
    }
    return 0
})

async function scrollToForecast() {
    // Wait for Vue to finish rendering after data load
    await nextTick();
    // Then poll in case child components are still rendering
    let attempts = 0;
    const scrollInterval = setInterval(() => {
        const el = document.getElementById('forecast_container');
        if (el && el.getBoundingClientRect().height > 0) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            clearInterval(scrollInterval);
        } else if (attempts >= 30) {
            clearInterval(scrollInterval); // stop trying after 3 seconds
        }
        attempts++;
    }, 100);
}

const weatherHeroStyle = computed(() => {
    if (!currentWeather.value) {
        return {}
    }

    return getWeatherBackground(WEATHER_VIEW_KEY)
})

const currentWeatherUpdatedAt = computed(() => {
    if (!currentWeather.value?.fetch_time) {
        return '—'
    }

    return new Date(currentWeather.value.fetch_time).toLocaleString(locale.value)
})

const osmEmbedUrl = computed(() => {
    if (!currentLocation.value) return ''
    const lat = currentLocation.value.latitude
    const lon = currentLocation.value.longitude
    const offset = 0.05
    return `https://www.openstreetmap.org/export/embed.html?bbox=${lon - offset},${lat - offset},${lon + offset},${lat + offset}&layer=mapnik&marker=${lat},${lon}`
})

const successMessage = ref('')

watch(routeQuery, async (query) => {
    successMessage.value = ''
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

// Watch for route changes (e.g., widget clicks when app is backgrounded)
// and reload weather data if needed
watch(() => route.fullPath, async (newPath, oldPath) => {
    if (oldPath && newPath !== oldPath && route.path === '/rest/weather') {
        const alreadyHasData = !!currentWeather.value

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

        if (route.query.day !== undefined) {
            await scrollToForecast()
        }
    }
})

onMounted(async () => {
    const alreadyHasData = !!currentWeather.value
    await loadSavedLocation()

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

    if (route.query.day !== undefined) {
        await scrollToForecast()
    }
})

function formatLocationLabel(location: WeatherLocationPayload): string {
    return [location.name, location.state || location.county, location.country]
        .filter(Boolean)
        .join(', ')
}

function getLocationKey(location: WeatherLocationPayload): string {
    return `${location.name}-${location.latitude}-${location.longitude}`
}

function getFlagIconUrl(countryCode: string): string {
    return `https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/7.3.2/flags/1x1/${countryCode.toLowerCase()}.svg`
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

async function selectLocation(location: WeatherLocationPayload): Promise<void> {
    successMessage.value = ''
    clearError()
    setCurrentLocation(location)
    await loadWeatherForLocation(location)
}

async function removeHomeLocation(): Promise<void> {
    successMessage.value = ''
    clearError()
    const deleted = await deleteLocation()
    if (!deleted) {
        return
    }

    successMessage.value = t('home_weather_removed')
}

async function refreshWeather(force = false): Promise<void> {
    successMessage.value = ''
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

    successMessage.value = ''
    clearError()
    const saved = await saveLocation(currentLocation.value, false)
    if (!saved) {
        return
    }

    successMessage.value = t('home_weather_saved')
}

async function removeSavedLocation(location: WeatherLocationPayload): Promise<void> {
    successMessage.value = ''
    clearError()

    const deleted = await removeSavedLocationEntry(location)
    if (!deleted) {
        return
    }

    successMessage.value = t('home_weather_removed')
}

async function setAsHome(location: WeatherLocationPayload): Promise<void> {
    successMessage.value = ''
    clearError()
    const saved = await setHomeLocation(location)
    if (!saved) {
        return
    }

    setCurrentLocation(saved)
    successMessage.value = t('saved_as_home')
}
</script>