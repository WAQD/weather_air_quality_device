<template>
    <div id="current_weather_card"
        class="order-2 xl:order-none card bg-base-100 shadow-xl overflow-hidden"
        :style="weatherHeroStyle">
        <div class="card-body p-3 sm:p-6 backdrop-blur-md" :class="weatherTintClass">
            <div class="flex items-start justify-between gap-3">
                <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] opacity-60">
                        {{ t('current_weather') }}</p>
                    <h1 class="mt-2 text-2xl sm:text-3xl font-bold">{{ t('home_weather') }}</h1>
                </div>
                <span v-if="cached && currentWeather" class="badge badge-info badge-outline">{{
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
                        <p class="text-4xl font-bold">{{ currentWeather.temp.toFixed(1) }}°C</p>
                        <p class="text-sm sm:text-base opacity-75">{{
                            translateWeatherCondition(currentWeather) }}</p>
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
                        :value="`${currentWeather.humidity.toFixed(0)}%`"
                        :icon-url="raindropIconUrl" />
                    <WeatherMetric icon-class="text-accent" :label="t('wind')"
                        :value="`${(currentWeather.wind_speed * 3.6).toFixed(1)} km/h`"
                        :icon-url="windDegIconUrl"
                        :rotate="((currentWeather.wind_deg ?? 0) + 180) % 360" />
                    <WeatherMetric icon-class="text-secondary" :label="t('pressure')"
                        :value="`${currentWeather.pressure.toFixed(0)} hPa`"
                        :icon-url="pressureIconUrl" />
                    <WeatherMetric icon-class="text-warning" :label="t('sunrise')"
                        :value="formatTimeString(currentWeather.sunrise)"
                        :icon-url="sunriseIconUrl" />
                    <WeatherMetric icon-class="text-orange-400" :label="t('sunset')"
                        :value="formatTimeString(currentWeather.sunset)"
                        :icon-url="sunsetIconUrl" />
                    <WeatherMetric icon-class="text-base-content/50" :label="t('elevation')"
                        :value="currentWeather.altitude ? `${Math.round(currentWeather.altitude)} m` : '-'"
                        :icon-url="altitudeIconUrl" />
                </div>
            </div>

            <div v-else
                class="mt-5 rounded-box border border-dashed border-base-300 bg-base-200/60 p-4 text-sm opacity-80">
                {{ t('home_weather_needs_location') }}
            </div>

            <div class="mt-5 flex flex-col gap-3">
                <button class="btn btn-secondary" type="button"
                    :disabled="isLoadingWeather || !currentLocation" @click="refreshWeather(true)">
                    {{ t('home_weather_refresh') }}
                </button>
                <button class="btn btn-ghost" type="button"
                    :disabled="isSavingLocation || !homeLocation" @click="removeHomeLocation">
                    {{ t('delete') }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import { useWeather } from '../composables/useWeather'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'
import { formatLocationLabel } from '../utils/weather'
import WeatherMetric from './WeatherMetric.vue'

const WEATHER_VIEW_KEY = 'website-weather-view'

const { t, locale } = useTranslation()
const { getWeatherBackground } = useWeather()
const {
    currentLocation,
    homeLocation,
    currentWeather,
    cached,
    isLoadingWeather,
    isRefreshingWeather,
    isSavingLocation,
    successMessage,
    clearSuccess,
    clearError,
    loadWeather,
    loadWeatherForLocation,
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
