<template>
    <div class="container mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8 max-w-full">
        <div class="grid grid-cols-1 gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
            <div class="space-y-6">
                <div class="card bg-base-100 shadow-xl overflow-hidden" :style="weatherHeroStyle">
                    <div class="bg-base-100/82 backdrop-blur-md">
                        <div class="card-body p-5 sm:p-6">
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
                                    <p class="text-sm opacity-70">{{ t('last_updated') }}: {{
                                        currentWeatherUpdatedAt }}</p>
                                </div>

                                <div class="grid grid-cols-2 gap-3 text-sm">
                                    <div class="rounded-box bg-base-200/80 p-3">
                                        <p class="text-xs uppercase tracking-[0.16em] opacity-60">{{
                                            t('humidity') }}</p>
                                        <p class="mt-1 text-lg font-semibold">{{
                                            currentWeather.humidity.toFixed(0) }}%</p>
                                    </div>
                                    <div class="rounded-box bg-base-200/80 p-3">
                                        <p class="text-xs uppercase tracking-[0.16em] opacity-60">{{
                                            t('wind') }}</p>
                                        <p class="mt-1 text-lg font-semibold">{{
                                            currentWeather.wind_speed.toFixed(1) }} m/s</p>
                                    </div>
                                    <div class="rounded-box bg-base-200/80 p-3">
                                        <p class="text-xs uppercase tracking-[0.16em] opacity-60">{{
                                            t('pressure') }}</p>
                                        <p class="mt-1 text-lg font-semibold">{{
                                            currentWeather.pressure.toFixed(0) }} hPa</p>
                                    </div>
                                    <div class="rounded-box bg-base-200/80 p-3">
                                        <p class="text-xs uppercase tracking-[0.16em] opacity-60">{{
                                            t('weather_clouds') }}</p>
                                        <p class="mt-1 text-lg font-semibold">{{
                                            currentWeather.clouds.toFixed(0) }}%</p>
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
                </div>

                <div class="card bg-base-100 shadow-xl">
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
                                <div class="flex items-center justify-between gap-3">
                                    <div class="min-w-0">
                                        <p class="font-semibold truncate">{{ location.name }}</p>
                                        <p class="text-xs opacity-70">{{ location.state ||
                                            location.country }}</p>
                                    </div>
                                    <div class="flex gap-2 shrink-0">
                                        <button class="btn btn-xs" type="button"
                                            @click="selectLocation(location)">{{ t('open')
                                            }}</button>
                                        <button class="btn btn-xs btn-outline" type="button"
                                            :disabled="isSavingLocation"
                                            @click="setAsHome(location)">{{ t('set_home')
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

            <div class="min-w-0 space-y-6">
                <div v-if="currentLocation"
                    class="rounded-box border border-base-300 bg-base-200/70 p-4">
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
                                <div
                                    class="text-2xl font-thin truncate whitespace-nowrap">
                                    {{ currentLocation.name }}</div>
                            </div>
                            <div class="shrink-0 text-right max-w-[11rem] sm:max-w-[16rem]">
                                <div class="text-xs uppercase font-semibold opacity-60 truncate">
                                    {{ currentLocation.state || currentLocation.county ||
                                    currentLocation.country }}
                                </div>
                                <div class="text-sm opacity-80 truncate">LAT: {{
                                    currentLocation.latitude.toFixed(3) }}, LONG: {{
                                    currentLocation.longitude.toFixed(3) }}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-else
                    class="rounded-box border border-dashed border-base-300 bg-base-200/60 p-4 text-sm opacity-80">
                    {{ t('home_weather_needs_location') }}
                </div>

                <div v-if="isLoadingWeather" class="card bg-base-100 shadow-xl">
                    <div class="card-body p-4 sm:p-6">
                        <div class="flex items-center gap-3 text-sm sm:text-base">
                            <span class="loading loading-spinner loading-md"></span>
                            <span>Loading forecast...</span>
                        </div>
                    </div>
                </div>
                <WeatherForecast v-else class="w-full" :title="t('home_weather_forecast_title')"
                    :forecast-data="forecastData" :daytime-hourly-data="hourlyDaytimeData"
                    :nighttime-hourly-data="hourlyNighttimeData" />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import WeatherForecast from '../components/WeatherForecast.vue'
import { useTranslation } from '../composables/useTranslation'
import { useWeather } from '../composables/useWeather'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'

const WEATHER_VIEW_KEY = 'website-weather-view'

const route = useRoute()
const { t, locale } = useTranslation()
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

const successMessage = ref('')

watch(currentWeather, (weather) => {
    if (weather) {
        setWeatherData(WEATHER_VIEW_KEY, weather)
        return
    }

    clearWeatherData(WEATHER_VIEW_KEY)
}, { immediate: true })

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

onMounted(async () => {
    await loadSavedLocation()

    if (currentLocation.value && (!homeLocation.value || getLocationKey(homeLocation.value) !== getLocationKey(currentLocation.value))) {
        await loadWeatherForLocation(currentLocation.value)
        return
    }

    await loadWeather()
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