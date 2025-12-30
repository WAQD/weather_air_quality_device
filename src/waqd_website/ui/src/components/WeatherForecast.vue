<template>
  <div class="card bg-base-100 shadow-xl">
    <div class="card-body">
      <h2 class="card-title">{{ title }}</h2>
      
      <!-- 5-Day Forecast Section -->
      <div v-if="forecastData && forecastData.length > 0" class="mb-6">
        <h3 class="font-semibold mb-4">{{ t('weekly_weather_forecast') }}</h3>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div v-for="(day, index) in forecastData.slice(0, 5)" :key="index" class="card bg-base-200 shadow-md">
            <div class="card-body p-4 text-center">
              <!-- Day label -->
              <h3 class="font-bold text-sm mb-2">
                {{ formatForecastDate(day.date_time) }}
              </h3>
              
              <!-- Weather icon -->
              <img 
                v-if="day.icon" 
                :src="`/static/weather_icons/${day.icon}.svg`" 
                :alt="day.main"
                class="h-12 w-12 mx-auto mb-2 weather-icon"
              />
              
              <!-- Weather condition -->
              <p class="text-xs opacity-70 mb-2">{{ day.main }}</p>
              
              <!-- Day temperature -->
              <div class="mb-2">
                <p class="text-xs opacity-70">{{ t('day') }}</p>
                <p class="font-bold">{{ day.temp_min.toFixed(0) }}° / {{ day.temp_max.toFixed(0) }}°</p>
              </div>
              
              <!-- Night temperature -->
              <div>
                <p class="text-xs opacity-70">{{ t('night') }}</p>
                <p class="text-sm">{{ day.temp_night_min.toFixed(0) }}° / {{ day.temp_night_max.toFixed(0) }}°</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Hourly Forecast Graph Section -->
      <div v-if="hasHourlyData" class="mt-6">
        <h3 class="font-semibold mb-4">{{ t('hourly_forecast') }}</h3>
        
        <!-- Toggle between day and night -->
        <div class="tabs tabs-boxed mb-4">
          <a 
            class="tab" 
            :class="{ 'tab-active': selectedPeriod === 'day' }"
            @click="selectedPeriod = 'day'"
          >
            {{ t('day')}} ({{ daytimeHourlyData?.length || 0 }} {{ t('hours')}})
          </a>
          <a 
            class="tab" 
            :class="{ 'tab-active': selectedPeriod === 'night' }"
            @click="selectedPeriod = 'night'"
          >
            {{ t('night')}} ({{ nighttimeHourlyData?.length || 0 }} {{ t('hours')}})
          </a>
        </div>

        <!-- Hourly data display -->
        <div class="overflow-x-auto">
          <div class="flex gap-2 pb-2">
            <div 
              v-for="(hour, index) in currentHourlyData" 
              :key="index"
              class="flex-shrink-0 card bg-base-200 p-3 min-w-[100px] text-center"
            >
              <p class="text-xs opacity-70 mb-1">{{ formatHourlyTime(hour.date_time) }}</p>
              <img 
                v-if="hour.icon" 
                :src="`/static/weather_icons/${hour.icon}.svg`" 
                :alt="hour.main"
                class="h-8 w-8 mx-auto mb-1 weather-icon"
              />
              <p class="font-bold">{{ hour.temp.toFixed(1) }}°</p>
              <p class="text-xs opacity-70">{{ hour.main }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- No data message -->
      <div v-if="!forecastData || forecastData.length === 0" class="text-center py-8 opacity-70">
        <p>{{'No forecast data available' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import type { ForecastData } from '../composables/useWeather'

const { t } = useTranslation()

interface HourlyWeatherData {
  main: string
  temp: number
  icon: string
  date_time: string
  wid: number
  wind_speed: number
  wind_deg: number
  sunrise: string
  sunset: string
  pressure: number
  pressure_sea_level: number
  humidity: number
  clouds: number
}

interface Props {
  title?: string
  forecastData?: ForecastData[]
  daytimeHourlyData?: HourlyWeatherData[][]
  nighttimeHourlyData?: HourlyWeatherData[][]
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Weather Forecast',
  forecastData: () => [],
  daytimeHourlyData: () => [],
  nighttimeHourlyData: () => []
})

const selectedPeriod = ref<'day' | 'night'>('day')

const hasHourlyData = computed(() => {
  return (props.daytimeHourlyData && props.daytimeHourlyData.length > 0) ||
         (props.nighttimeHourlyData && props.nighttimeHourlyData.length > 0)
})

const currentHourlyData = computed(() => {
  if (selectedPeriod.value === 'day') {
    // Flatten the array of arrays and get first day's hourly data
    return props.daytimeHourlyData?.[0] || []
  } else {
    return props.nighttimeHourlyData?.[0] || []
  }
})

function formatForecastDate(dateString: string): string {
  const date = new Date(dateString)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  
  // Check if it's today
  if (date.toDateString() === today.toDateString()) {
    return t('today')
  }
  
  // Check if it's tomorrow
  if (date.toDateString() === tomorrow.toDateString()) {
    return t('tomorrow')
  }
  
  // Otherwise return weekday name
  return date.toLocaleDateString(undefined, { weekday: 'short' })
}

function formatHourlyTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString(undefined, { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  })
}
</script>

<style scoped>
.weather-icon {
  filter: brightness(0) invert(1);
}
</style>
