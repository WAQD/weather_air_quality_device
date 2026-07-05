<template>
    <div class="scroll-container">
        <div class="hero hero-bg-main min-h-screen snap-section relative">
            <div class="hero-overlay bg-opacity-60"></div>
            <div class="hero-content flex-col max-w-7xl w-full px-4 sm:px-6 lg:px-8 relative z-10">
                <div class="text-center glass rounded-box p-4 sm:p-6 lg:p-8 bg-primary/80 backdrop-blur-sm max-w-full">
                    <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold">{{
                        t('home_build_station') }}</h1>
                    <p class="py-4 sm:py-6 text-base sm:text-lg">
                        {{ t('home_create_professional') }}
                    </p>
                    <router-link to="/public/login" class="btn btn-secondary btn-lg relative mt-2">
                        {{ t('login') }}
                        <span
                            class="absolute -top-2 -right-2 badge badge-warning badge-sm font-bold z-10 animate-pulse">Beta</span>
                    </router-link>
                </div>
            </div>

            <div class="absolute bottom-16 left-1/2 transform -translate-x-1/2 z-10 animate-bounce">
                <div class="flex flex-col items-center text-white opacity-80">
                    <span class="text-sm mb-2">{{ t('home_scroll_more') }}</span>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none"
                        viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </div>
        </div>

        <div class="hero hero-bg-features min-h-screen snap-section">
            <div class="hero-overlay bg-opacity-70"></div>
            <div
                class="hero-content flex-col lg:flex-row max-w-7xl w-full gap-4 sm:gap-6 px-4 sm:px-6 lg:px-8 relative z-10">
                <div class="w-full lg:w-3/5 flex justify-center">
                    <img :src="mainGuiImg" alt="WAQD Main Interface"
                        class="rounded-lg shadow-2xl w-full max-w-[600px]" />
                </div>
                <div
                    class="lg:w-2/5 glass rounded-box p-4 sm:p-6 bg-base-100/90 backdrop-blur-sm max-w-full">
                    <h2 class="text-2xl sm:text-3xl lg:text-4xl font-bold mb-4">{{
                        t('home_full_featured') }}</h2>
                    <ul class="space-y-2 text-base">
                        <li class="flex items-start">
                            <span class="text-3xl mr-2">🌡️</span>
                            <span>{{ t('home_interior_temp') }}</span>
                        </li>
                        <li class="flex items-start">
                            <span class="text-3xl mr-2">🌤️</span>
                            <span>{{ t('home_exterior_weather') }}</span>
                        </li>
                        <li class="flex items-start">
                            <span class="text-3xl mr-2">📅</span>
                            <span>{{ t('home_forecast_3day') }}</span>
                        </li>
                        <li class="flex items-start">
                            <span class="text-3xl mr-2">💨</span>
                            <span>{{ t('home_air_quality') }}</span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="hero hero-bg-hardware min-h-screen snap-section">
            <div class="hero-overlay bg-opacity-70"></div>
            <div
                class="hero-content flex-col lg:flex-row max-w-7xl w-full gap-4 sm:gap-6 px-4 sm:px-6 lg:px-8 relative z-10">
                <div class="w-full lg:w-1/2 flex justify-center">
                    <img :src="waqdStationImg" alt="WAQD Station"
                        class="rounded-lg shadow-2xl w-full max-w-[600px]" />
                </div>
                <div
                    class="lg:w-1/2 glass rounded-box p-4 sm:p-6 bg-base-100/90 backdrop-blur-sm max-w-full">
                    <h2 class="text-2xl sm:text-3xl font-bold mb-4">{{ t('home_easy_assembly') }}
                    </h2>
                    <p class="text-base mb-3">
                        {{ t('home_assembly_desc') }}
                    </p>
                    <div class="grid grid-cols-2 gap-3">
                        <div class="bg-base-200 rounded-lg p-3">
                            <h3 class="font-bold text-base mb-1">🔧 {{ t('home_raspberry_pi') }}
                            </h3>
                            <p class="text-sm">{{ t('home_raspberry_versions') }}</p>
                        </div>
                        <div class="bg-base-200 rounded-lg p-3">
                            <h3 class="font-bold text-base mb-1">📺 {{ t('display') }}</h3>
                            <p class="text-sm">{{ t('home_display_types') }}</p>
                        </div>
                        <div class="bg-base-200 rounded-lg p-3">
                            <h3 class="font-bold text-base mb-1">🌡️ {{ t('home_sensors') }}</h3>
                            <p class="text-sm">{{ t('home_sensor_types') }}</p>
                        </div>
                        <div class="bg-base-200 rounded-lg p-3">
                            <h3 class="font-bold text-base mb-1">📦 {{ t('home_case') }}</h3>
                            <p class="text-sm">{{ t('home_case_recommended') }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="hero hero-bg-3dprint min-h-screen snap-section">
            <div class="hero-overlay bg-opacity-70"></div>
            <div
                class="hero-content flex-col lg:flex-row max-w-7xl w-full gap-4 sm:gap-6 px-4 sm:px-6 lg:px-8 relative z-10">
                <div class="w-full lg:w-2/5 flex justify-center">
                    <img :src="sensorCaseImg" alt="3D Printable Sensor Case"
                        class="rounded-lg shadow-2xl w-full max-w-[500px]" />
                </div>
                <div
                    class="lg:w-3/5 glass rounded-box p-4 sm:p-6 bg-base-100/90 backdrop-blur-sm max-w-full">
                    <h2 class="text-2xl sm:text-3xl lg:text-4xl font-bold mb-4">{{
                        t('home_3d_printable') }}</h2>
                    <p class="text-base sm:text-lg lg:text-xl mb-3">
                        {{ t('home_3d_desc') }}
                    </p>
                    <ul class="space-y-2 text-base">
                        <li class="flex items-start">
                            <span class="text-2xl mr-2">📦</span>
                            <span>{{ t('home_3d_sensors') }}</span>
                        </li>
                        <li class="flex items-start">
                            <span class="text-2xl mr-2">💨</span>
                            <span>{{ t('home_3d_ventilation') }}</span>
                        </li>
                        <li class="flex items-start">
                            <span class="text-2xl mr-2">🔌</span>
                            <span>{{ t('home_3d_cable') }}</span>
                        </li>
                        <li class="flex items-start">
                            <span class="text-2xl mr-2">🔩</span>
                            <span>{{ t('home_3d_screws') }}</span>
                        </li>
                    </ul>
                    <div class="mt-4">
                        <p class="text-lg opacity-70">{{ t('home_3d_stl') }}</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="hero hero-bg-custom min-h-screen snap-section">
            <div class="hero-overlay bg-opacity-70"></div>
            <div
                class="hero-content flex-col lg:flex-row max-w-7xl w-full gap-4 px-4 sm:px-6 lg:px-8 relative z-10">
                <div class="w-full lg:w-4/6 flex justify-center">
                    <img :src="optionsImg" alt="WAQD Options"
                        class="rounded-lg shadow-2xl w-full max-w-[700px]" />
                </div>
                <div
                    class="lg:w-2/6 glass rounded-box p-4 sm:p-6 bg-base-100/90 backdrop-blur-sm max-w-full">
                    <h2 class="text-2xl sm:text-3xl lg:text-4xl font-bold mb-4">{{
                        t('home_customizable') }}</h2>
                    <p class="text-base sm:text-lg lg:text-xl mb-4">
                        {{ t('home_customizable_desc') }}
                    </p>
                    <div class="grid grid-cols-2 gap-3">
                        <div class="card bg-base-200 shadow-xl">
                            <div class="card-body p-4">
                                <h3 class="card-title text-xl">🌍 {{ t('location') }}</h3>
                                <p class="text">{{ t('home_location_desc') }}</p>
                            </div>
                        </div>
                        <div class="card bg-base-200 shadow-xl">
                            <div class="card-body p-4">
                                <h3 class="card-title text-xl">🎨 {{ t('display') }}</h3>
                                <p class="text">{{ t('home_display_settings') }}</p>
                            </div>
                        </div>
                        <div class="card bg-base-200 shadow-xl">
                            <div class="card-body p-4">
                                <h3 class="card-title text-xl">🌐 {{ t('language') }}</h3>
                                <p class="text">{{ t('home_language_desc') }}</p>
                            </div>
                        </div>
                        <div class="card bg-base-200 shadow-xl">
                            <div class="card-body p-4">
                                <h3 class="card-title text-xl">☁️ {{ t('home_weather') }}</h3>
                                <p class="text">{{ t('home_weather_desc') }}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="hero hero-bg-cta min-h-[60vh] snap-section">
            <div class="hero-overlay bg-opacity-60"></div>
            <div class="hero-content text-center max-w-5xl px-4 sm:px-6 lg:px-8 relative z-10">
                <div
                    class="glass rounded-box p-6 sm:p-8 lg:p-12 bg-primary/80 backdrop-blur-sm max-w-full">
                    <h2 class="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6">{{
                        t('home_ready_building') }}</h2>
                    <p class="text-base sm:text-lg lg:text-xl mb-6 sm:mb-8">
                        {{ t('home_build_register') }}
                    </p>
                    <div class="flex flex-wrap gap-3 sm:gap-4 justify-center">
                        <a href="https://github.com/WAQD/weather_air_quality_device/releases/latest/download/waqd-app-release.apk"
                            class="btn btn-sm sm:btn-md lg:btn-lg whitespace-normal h-auto min-h-[3rem] py-2 bg-[#3DDC84] border-[#3DDC84] text-black hover:bg-[#2bb870] hover:border-[#2bb870]">
                            <!-- Android head -->
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M17.6 9.48l1.84-3.18c.16-.31.04-.69-.26-.85a.637.637 0 0 0-.85.26l-1.87 3.23C14.96 8.17 13.54 7.8 12 7.8s-2.96.37-4.46 1.14L5.67 5.71a.637.637 0 0 0-.85-.26c-.3.16-.42.54-.26.85l1.84 3.18C3.6 11.07 1.96 13.6 1.96 16.4h20.08c0-2.8-1.64-5.33-4.44-6.92zM8.68 13.8a.8.8 0 1 1 0-1.6.8.8 0 0 1 0 1.6zm6.64 0a.8.8 0 1 1 0-1.6.8.8 0 0 1 0 1.6z"/>
                            </svg>
                            {{ t('home_download_android') }}
                        </a>
                        <a href="https://github.com/WAQD/weather_air_quality_device/wiki/Assembly-and-Software-Setup-Guide"
                            target="_blank" class="btn btn-secondary btn-sm sm:btn-md lg:btn-lg whitespace-normal h-auto min-h-[3rem] py-2">
                            <svg class="h-6 w-6 mr-2 shrink-0">
                                <use :href="taskListIconUrl" fill="currentColor" />
                            </svg>
                            {{ t('home_view_assembly') }}
                        </a>
                        <a href="https://github.com/goszpeti/weather_air_quality_device"
                            target="_blank" class="btn btn-secondary btn-sm sm:btn-md lg:btn-lg whitespace-normal h-auto min-h-[3rem] py-2">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2 shrink-0"
                                viewBox="0 0 24 24" fill="currentColor">
                                <path
                                    d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                            </svg>
                            {{ t('home_view_github') }}
                        </a>
                        <router-link to="/public/about"
                            class="btn btn-primary btn-secondary btn-sm sm:btn-md lg:btn-lg whitespace-normal h-auto min-h-[3rem] py-2">
                            <svg class="h-6 w-6 mr-2 shrink-0">
                                <use :href="infoIconUrl" fill="currentColor" />
                            </svg>
                            {{ t('settings_tab_about') }}
                        </router-link>
                    </div>
                    <p class="mt-8 text-base opacity-80">
                        🗲 {{ t('home_open_source') }}
                    </p>
                    <p class="mt-2 text-base opacity-80">
                        v{{ version }} Copyright (c) 2026 Péter Gosztolya and contributors.
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'
import { useUser } from '../composables/useUser'

const router = useRouter()
const { t } = useTranslation()
const { isLoggedIn, fetchUserInfo, isLoading: isUserLoading } = useUser()
const version = __APP_VERSION__

onMounted(async () => {
    if (!isLoggedIn.value && !isUserLoading.value) {
        await fetchUserInfo()
    }
    
    if (isLoggedIn.value) {
        router.push('/home')
    }
})

const taskListIconUrl = '/static/general_icons/task_list.svg#main'
const infoIconUrl = '/static/general_icons/info.svg#main'

const mainGuiImg = '/static/doc_images/main_gui.png'
const waqdStationImg = '/static/doc_images/waqd_station.jpg'
const sensorCaseImg = '/static/doc_images/sensor_case.png'
const optionsImg = '/static/doc_images/options.png'
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

.hero-bg-features {
    background-image: url(/static/gui_base/wolfgang-hasselmann-bR_-gllg7Bs-unsplash.avif);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.hero-bg-hardware {
    background-image: url(/static/gui_base/ish-consul-Ozlzi3DXuGg-unsplash.avif);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.hero-bg-3dprint {
    background-image: url(/static/gui_base/miguel-dias-coelho-ZbGwGW_u8zI-unsplash.avif);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.hero-bg-custom {
    background-image: url(/static/gui_base/joe-r-harris-KOnl4LFvwHE-unsplash.avif);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

.hero-bg-cta {
    background-image: url(/static/gui_base/gaspar-uhas-Y3vsGbFCX-o-unsplash.avif);
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}

@keyframes bounce {

    0%,
    100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-10px);
    }
}

.animate-bounce {
    animation: bounce 2s infinite;
}
</style>