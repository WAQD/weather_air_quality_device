<template>
    <div id="forecast_container"
        class="order-3 flex flex-col xl:block xl:min-w-0 xl:space-y-3 xl:sm:space-y-6">
        <div v-if="isLoadingWeather" id="forecast_loading" class="card bg-base-100 shadow-xl">
            <div class="card-body p-4 sm:p-6">
                <div class="flex items-center gap-3 text-sm sm:text-base">
                    <span class="loading loading-spinner loading-md"></span>
                    <span>Loading forecast...</span>
                </div>
            </div>
        </div>
        <WeatherForecast v-else class="w-full" :title="t('home_weather_forecast_title')"
            :forecast-data="forecastData" :daytime-hourly-data="hourlyDaytimeData"
            :nighttime-hourly-data="hourlyNighttimeData" :initial-day-index="initialDayIndex" />

        <WeatherMapCard />
    </div>
</template>

<script setup lang="ts">
import { useTranslation } from '../composables/useTranslation'
import { useWebsiteWeather } from '../composables/useWebsiteWeather'
import WeatherForecast from './WeatherForecast.vue'
import WeatherMapCard from './WeatherMapCard.vue'

defineProps<{
    initialDayIndex: number
}>()

const { t } = useTranslation()
const {
    isLoadingWeather,
    forecastData,
    hourlyDaytimeData,
    hourlyNighttimeData
} = useWebsiteWeather()
</script>
