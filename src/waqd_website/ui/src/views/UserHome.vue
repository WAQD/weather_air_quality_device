<template>
    <div class="scroll-container">
        <div class="hero hero-bg-main min-h-screen snap-section relative">
            <div class="hero-overlay bg-opacity-60"></div>
            <div class="hero-content flex-col max-w-7xl w-full px-4 sm:px-6 lg:px-8 relative z-10">
                <div
                    class="w-full glass rounded-box p-4 sm:p-6 lg:p-8 bg-primary/80 backdrop-blur-sm text-center lg:text-left">
                    <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold">{{
                        t('home_welcome_back', { username }) }}</h1>
                </div>

                <div class="grid w-full gap-4 mt-4 sm:mt-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)] lg:gap-6">
                    <!-- Devices: second on mobile, left on desktop -->
                    <div
                        class="order-2 lg:order-1 glass rounded-box p-4 sm:p-6 lg:p-8 bg-primary/80 backdrop-blur-sm max-w-full text-center lg:text-left">
                        <p class="py-2 sm:py-4 text-base sm:text-lg">
                            {{ t('home_manage_devices') }}
                            <a class="link text-purple-300"
                                href="https://github.com/goszpeti/weather_air_quality_device">
                                WAQD
                            </a>
                            {{ t('home_manage_devices_desc') }}
                        </p>
                        <div class="mt-2">
                            <DeviceCard v-if="homeDevice" :device="homeDevice"
                                :show-management-actions="false" @connect="connectToDevice" />
                            <router-link v-else to="/rest/devices"
                                class="btn btn-secondary btn-md sm:btn-lg">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2"
                                    viewBox="0 0 20 20" fill="currentColor">
                                    <path
                                        d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
                                </svg>
                                {{ t('home_go_to_devices') }}
                            </router-link>
                        </div>
                    </div>

                    <!-- Weather: first on mobile, right on desktop -->
                    <div
                        class="order-1 lg:order-2 glass rounded-box p-4 sm:p-6 bg-base-100/90 backdrop-blur-sm max-w-full text-base-content shadow-2xl">
                        <div class="flex items-start justify-between gap-3">
                            <div>
                                <p
                                    class="text-xs font-semibold uppercase tracking-[0.24em] opacity-70">
                                    {{ t('current_weather') }}</p>
                                <h2 class="mt-2 text-2xl sm:text-3xl font-bold">{{
                                    t('home_weather_today') }}</h2>
                                <p class="mt-2 text-sm sm:text-base opacity-80">{{ 
                                    locationMode === 'gps' && currentLocation ? formatLocationLabel(currentLocation) :
                                    homeLocation ? formatLocationLabel(homeLocation) :
                                    t('home_weather_needs_location') }}</p>
                                <div class="mt-3 join">
                                    <button class="btn btn-xs join-item" :class="locationMode === 'home' ? 'btn-primary' : 'btn-ghost'" @click="setLocationMode('home')">
                                        🏠 {{ t('home') }}
                                    </button>
                                    <button class="btn btn-xs join-item" :class="locationMode === 'gps' ? 'btn-primary' : 'btn-ghost'" @click="setLocationMode('gps')">
                                        🛰️ GPS
                                    </button>
                                </div>
                                <div v-if="Capacitor.isNativePlatform()" class="mt-2 join">
                                    <button class="btn btn-xs join-item" :class="widgetStyle === 'simple' ? 'btn-neutral' : 'btn-ghost'" @click="setWidgetStyle('simple')">
                                        Widget: {{ t('simple') || 'Simple' }}
                                    </button>
                                    <button class="btn btn-xs join-item" :class="widgetStyle === 'forecast' ? 'btn-neutral' : 'btn-ghost'" @click="setWidgetStyle('forecast')">
                                        Widget: {{ t('weekly_weather_forecast') || 'Forecast' }}
                                    </button>
                                </div>
                            </div>
                            <span v-if="cached && currentWeather"
                                class="badge badge-info badge-outline whitespace-nowrap">
                                {{ t('home_weather_cached') }}
                            </span>
                        </div>

                        <div v-if="currentWeather" class="mt-5 space-y-4">
                            <div class="flex items-center gap-4">
                                <img v-if="currentWeather.icon"
                                    :src="`/static/weather_icons/${currentWeather.icon}.svg`"
                                    :alt="currentWeather.main"
                                    class="h-16 w-16 brightness-0 invert-0 weather-icon" />
                                <div>
                                    <h3 class="text-4xl font-bold">{{ currentWeather.temp.toFixed(1)
                                        }}°C</h3>
                                    <p class="text-base opacity-80">{{
                                        translateWeatherCondition(currentWeather) }}</p>
                                </div>
                            </div>

                            <div class="grid grid-cols-1 gap-3 text-sm">
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
                                        (currentWeather.wind_speed * 3.6).toFixed(1) }} km/h</p>
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

                            <div class="flex flex-col gap-3 sm:flex-row">
                                <button class="btn btn-secondary" type="button"
                                    :disabled="isLoadingWeather || (!homeLocation && locationMode === 'home')"
                                    @click="refreshWeather(true)">
                                    {{ t('home_weather_refresh') }}
                                </button>
                                <router-link to="/rest/weather" class="btn btn-outline">
                                    {{ t('home_weather_details') }}
                                </router-link>
                            </div>
                        </div>

                        <div v-else
                            class="mt-4 rounded-box border border-dashed border-base-300 bg-base-200/60 p-4 text-sm opacity-80">
                            {{ t('home_weather_needs_location') }}
                            <div class="mt-3">
                                <router-link to="/rest/weather" class="btn btn-secondary btn-sm">
                                    {{ t('home_weather_manage') }}
                                </router-link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { App } from '@capacitor/app'
import { useTranslation } from '../composables/useTranslation'
import { useUser } from '../composables/useUser'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'
import { useWeather } from '../composables/useWeather'
import DeviceCard from '../components/DeviceCard.vue'
import type { Device } from '../types/device'

const router = useRouter()
const { t } = useTranslation()
const { isLoggedIn, username, fetchUserInfo, isLoading: isUserLoading } = useUser()
const { setWeatherData } = useWeather()
const {
    homeLocation,
    currentLocation,
    currentWeather,
    cached,
    isLoadingWeather,
    locationMode,
    widgetStyle,
    loadSavedLocation,
    loadWeather,
    setLocationMode,
    setWidgetStyle,
    loadWeatherByGps
} = useWebsiteWeather()

const devices = ref<Device[]>([])
const homeDevice = computed(() => devices.value[0] || null)

let weatherInterval: any = null

watch(isLoggedIn, async (loggedIn) => {
    if (!loggedIn) {
        devices.value = []
        stopWeatherPolling()
        router.push('/public/login')
        return
    }

    await Promise.all([
        initializeHomeWeather(),
        loadDevices()
    ])
    startWeatherPolling()
}, { immediate: true })

onMounted(async () => {
    if (!isLoggedIn.value && !isUserLoading.value) {
        await fetchUserInfo()
    }

    if (!isLoggedIn.value && !isUserLoading.value) {
        router.push('/public/login')
        return
    }

    try {
        App.addListener('appStateChange', ({ isActive }) => {
            if (isActive) {
                startWeatherPolling()
                refreshWeather(false)
            } else {
                stopWeatherPolling()
            }
        })
    } catch {
        // Not on mobile
    }

    window.addEventListener('waqd-widget-gps-refresh', handleWidgetGpsRefresh)
})

onUnmounted(() => {
    stopWeatherPolling()
    window.removeEventListener('waqd-widget-gps-refresh', handleWidgetGpsRefresh)
})

function startWeatherPolling() {
    stopWeatherPolling()
    if (!isLoggedIn.value) return
    // Refresh weather every 30 minutes while app is in foreground
    weatherInterval = setInterval(() => refreshWeather(), 30 * 60 * 1000)
}

function stopWeatherPolling() {
    if (weatherInterval) {
        clearInterval(weatherInterval)
        weatherInterval = null
    }
}

async function handleWidgetGpsRefresh(): Promise<void> {
    if (isLoggedIn.value && locationMode.value === 'gps') {
        await refreshWeather(true)
    }
}

async function initializeHomeWeather(): Promise<void> {
    await loadSavedLocation()
    await loadWeather()
}

async function loadDevices(): Promise<void> {
    try {
        const response = await fetch('/api/user/devices', {
            credentials: 'include'
        })

        if (!response.ok) {
            throw new Error('Failed to load devices')
        }

        const data = await response.json()
        devices.value = data.devices || []

        devices.value.forEach(device => {
            if (device.weather) {
                setWeatherData(device.device_id, device.weather)
            }
        })
    } catch (error) {
        console.error('Error loading home devices:', error)
        devices.value = []
    }
}

function connectToDevice(device: Device): void {
    router.push(`/rest/device/${device.id}`)
}

function formatLocationLabel(location: WeatherLocationPayload): string {
    return [location.name, location.state || location.county, location.country]
        .filter(Boolean)
        .join(', ')
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

async function refreshWeather(force = false): Promise<void> {
    if (locationMode.value === 'gps') {
        await loadWeatherByGps()
    } else {
        await loadWeather(force)
    }
}
</script>

<style scoped>
.scroll-container {
    overflow-y: auto;
    overflow-x: hidden;
    height: calc(100vh - 4rem);
    width: 100%;
    max-width: 100vw;
}

@media (min-width: 768px) {
    .scroll-container {
        scroll-snap-type: y mandatory;
    }
}

.snap-section {
    overflow-x: hidden;
    max-width: 100vw;
}

@media (min-width: 768px) {
    .snap-section {
        scroll-snap-align: start;
        scroll-snap-stop: always;
    }
}

.snap-section img {
    max-width: 100%;
    height: auto;
}

.hero-content {
    max-width: 100%;
    box-sizing: border-box;
}

.hero-bg-main {
    background-image: url(/static/gui_base/pascal-debrunner-UjyUlxr1Yjo-unsplash.avif);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}
</style>