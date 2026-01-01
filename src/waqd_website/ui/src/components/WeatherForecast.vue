<template>
  <div class="card bg-base-100 shadow-xl">
    <div class="card-body p-4 sm:p-6">
      <h2 class="card-title text-base sm:text-lg">{{ title }}</h2>
      
      <!-- 5-Day Forecast Section -->
      <div v-if="forecastData && forecastData.length > 0" class="mb-4 sm:mb-6">
        <h3 class="font-semibold text-sm sm:text-base mb-3 sm:mb-4">{{ t('weekly_weather_forecast') }}</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3 lg:gap-4">
          <div v-for="(day, index) in forecastData.slice(0, 5)" :key="index" class="card bg-base-200 shadow-md">
            <div class="card-body p-2 sm:p-3 lg:p-4 text-center">
              <!-- Day label -->
              <h3 class="font-bold text-sm sm:text-base mb-1 sm:mb-2">
                {{ formatForecastDate(day.date_time) }}
              </h3>
              
              <!-- Weather icon -->
              <img 
                v-if="day.icon" 
                :src="`/static/weather_icons/${day.icon}.svg`" 
                :alt="day.main"
                class="h-10 w-10 sm:h-12 sm:w-12 lg:h-14 lg:w-14 mx-auto mb-1 sm:mb-2 weather-icon"
              />
              
              <!-- Weather condition -->
              <p class="text-sm opacity-70 mb-1 sm:mb-2 truncate">{{ translateWeatherCondition(day) }}</p>
              
              <!-- Day temperature -->
              <div class="mb-1 sm:mb-2">
                <p class="text-sm opacity-70">{{ t('day') }}</p>
                <p class="font-bold text-sm sm:text-base">{{ day.temp_min.toFixed(0) }}° / {{ day.temp_max.toFixed(0) }}°</p>
              </div>
              
              <!-- Night temperature -->
              <div>
                <p class="text-sm opacity-70">{{ t('night') }}</p>
                <p class="text-sm sm:text-base">{{ day.temp_night_min.toFixed(0) }}° / {{ day.temp_night_max.toFixed(0) }}°</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Hourly Forecast Graph Section -->
      <div v-if="hasHourlyData" class="mt-4 sm:mt-6">
        <h3 class="font-semibold text-sm sm:text-base mb-3 sm:mb-4">
          {{ t('hourly_forecast') }} ({{ mergedHourlyData.length }} {{ t('hours')}})
        </h3>

        <!-- Hourly data display in 2 rows max -->
        <div class="space-y-2 sm:space-y-3">
          <div 
            v-for="(row, rowIndex) in chunkedHourlyData" 
            :key="rowIndex"
            class="overflow-x-auto -mx-2 px-2"
          >
            <div class="flex gap-2 pb-2 min-w-max">
              <div 
                v-for="(hour, index) in row" 
                :key="index"
                class="flex-shrink-0 card bg-base-200 p-2 sm:p-3 min-w-[90px] sm:min-w-[110px] text-center"
              >
                <p class="text-sm opacity-70 mb-1">{{ formatHourlyTime(hour.date_time) }}</p>
                <img 
                  v-if="hour.icon" 
                  :src="`/static/weather_icons/${hour.icon}.svg`" 
                  :alt="hour.main"
                  class="h-8 w-8 sm:h-10 sm:w-10 mx-auto mb-1 weather-icon"
                />
                <p class="font-bold text-base sm:text-lg">{{ hour.temp.toFixed(1) }}°</p>
                <p class="text-sm opacity-70 truncate">{{ translateWeatherCondition(hour) }}</p>
              </div>
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

const hasHourlyData = computed(() => {
  return (props.daytimeHourlyData && props.daytimeHourlyData.length > 0) ||
         (props.nighttimeHourlyData && props.nighttimeHourlyData.length > 0)
})

// Translate weather condition based on wid or main
function translateWeatherCondition(weather: { wid?: number, main?: string }): string {
  // Try wid first (Open Meteo code)
  if (weather.wid !== undefined) {
    const key = `weather_${weather.wid}`
    const translated = t(key)
    if (translated !== key) {
      return translated
    }
  }
  
  // Fall back to main string (lowercase for consistency)
  if (weather.main) {
    const key = `weather_${weather.main.toLowerCase()}`
    const translated = t(key)
    if (translated !== key) {
      return translated
    }
    // If no translation found, return the main string as is
    return weather.main
  }
  
  return ''
}

// Merge day and night hourly data, sorted by time
const mergedHourlyData = computed(() => {
  const allHours: HourlyWeatherData[] = []
  
  // Add all daytime hours (first day only)
  if (props.daytimeHourlyData && props.daytimeHourlyData.length > 0) {
    allHours.push(...(props.daytimeHourlyData[0] || []))
  }
  
  // Add all nighttime hours (first day only)
  if (props.nighttimeHourlyData && props.nighttimeHourlyData.length > 0) {
    allHours.push(...(props.nighttimeHourlyData[0] || []))
  }
  
  // Sort by date_time chronologically
  return allHours.sort((a, b) => {
    return new Date(a.date_time).getTime() - new Date(b.date_time).getTime()
  })
})

// Chunk hourly data into 2 rows max
const chunkedHourlyData = computed(() => {
  const data = mergedHourlyData.value
  const halfLength = Math.ceil(data.length / 2)
  
  if (data.length === 0) return []
  if (data.length <= halfLength) return [data]
  
  return [
    data.slice(0, halfLength),
    data.slice(halfLength)
  ]
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
  
  // Otherwise return translated weekday name
  const weekdayMap: Record<number, string> = {
    0: 'weekday_sun',
    1: 'weekday_mon',
    2: 'weekday_tue',
    3: 'weekday_wed',
    4: 'weekday_thu',
    5: 'weekday_fri',
    6: 'weekday_sat'
  }
  
  const weekdayKey = weekdayMap[date.getDay()]!
  return t(weekdayKey)
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
