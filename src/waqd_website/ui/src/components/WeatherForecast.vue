<template>
  <div class="card bg-base-100 shadow-xl min-w-0">
    <div class="card-body p-4 sm:p-6 min-w-0">
      <h2 class="card-title text-base sm:text-lg">{{ title }}</h2>

      <!-- 7-Day Forecast Section -->
      <div v-if="forecastData && forecastData.length > 0" class="mb-4 sm:mb-6">
        <h3 class="font-semibold text-sm sm:text-base mb-3 sm:mb-4">{{ t('weekly_weather_forecast')
          }}</h3>
        <div class="overflow-x-auto w-full max-w-full -mx-2 px-2">
          <div class="flex gap-2 sm:gap-3 lg:gap-4 pt-1 pb-2 min-w-max">
            <button v-for="(day, index) in displayedForecastData" :key="index" type="button"
              class="card bg-base-200 shadow-md text-left transition-all duration-150 flex-shrink-0 min-w-[150px] sm:min-w-[170px]"
              :class="selectedDayIndex === index ? 'ring-2 ring-primary bg-base-300' : 'hover:bg-base-300/70'"
              @click="selectDay(index)">
              <div class="card-body p-2 sm:p-3 lg:p-4 text-center">
                <!-- Day label -->
                <h3 class="font-bold text-sm sm:text-base mb-1 sm:mb-2">
                  {{ formatForecastDate(day.date_time) }}
                </h3>

                <!-- Weather icon -->
                <img v-if="day.icon" :src="`/static/weather_icons/${day.icon}.svg`" :alt="day.main"
                  class="h-10 w-10 sm:h-12 sm:w-12 lg:h-14 lg:w-14 mx-auto mb-1 sm:mb-2 weather-icon" />

                <!-- Weather condition -->
                <p class="text-sm opacity-70 mb-1 sm:mb-2 truncate">{{
                  translateWeatherCondition(day) }}</p>

                <!-- Day temperature -->
                <div class="mb-1 sm:mb-2">
                  <p class="text-sm opacity-70">{{ t('day') }}</p>
                  <p class="font-bold text-sm sm:text-base">{{ day.temp_min.toFixed(0) }}° / {{
                    day.temp_max.toFixed(0) }}°</p>
                </div>

                <!-- Night temperature -->
                <div class="mb-1 sm:mb-2">
                  <p class="text-sm opacity-70">{{ t('night') }}</p>
                  <p class="text-sm sm:text-base">{{ day.temp_night_min.toFixed(0) }}° / {{
                    day.temp_night_max.toFixed(0) }}°</p>
                </div>

                <!-- Precipitation probability -->
                <div
                  v-if="day.precipitation_probability_max !== undefined || day.precipitation !== undefined"
                  class="space-y-1">
                  <p v-if="day.precipitation_probability_max !== undefined"
                    class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <img :src="raindropIconUrl" alt="Raindrop" class="h-10 w-10 weather-icon" />
                    {{ day.precipitation_probability_max.toFixed(0) }}%
                  </p>
                  <p v-if="day.precipitation !== undefined"
                    class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <img :src="showersIconUrl" alt="Showers" class="h-10 w-10 weather-icon" />
                    {{ day.precipitation.toFixed(1) }}mm
                  </p>
                </div>
                <!-- Daily wind display (moved from details) -->
                <div v-if="day.wind_speed !== undefined || day.wind_deg !== undefined"
                  class="mt-2 sm:mt-3 space-y-1">
                  <p class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <svg v-if="day.wind_deg !== undefined" class="h-8 w-8 weather-icon" aria-hidden="true"
                      :style="{ transform: `rotate(${((day.wind_deg ?? 0) + 180) % 360}deg)`, transformOrigin: 'center' }">
                      <use :href="windDegIconUrl" fill="currentColor" />
                    </svg>
                    {{ formatWind(day.wind_speed, day.wind_deg) }}
                  </p>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- Hourly Forecast Graph Section -->
      <div v-if="hasHourlyData" class="mt-4 sm:mt-6">
        <h3 class="font-semibold text-sm sm:text-base mb-3 sm:mb-4">
          {{ t('hourly_forecast') }} ({{ mergedHourlyData.length }} {{ t('hours') }})
        </h3>

        <!-- Hourly data display in a single row -->
        <div ref="hourlyScroller" class="overflow-x-auto w-full max-w-full -mx-2 px-2">
          <div class="flex gap-2 pt-1 pb-2 min-w-max">
            <div v-for="(hour, index) in mergedHourlyData" :key="index"
              class="hourly-card flex-shrink-0 card bg-base-200 p-2 sm:p-3 min-w-[90px] sm:min-w-[110px] text-center"
              :data-hour="getHourFromDateString(hour.date_time)">
              <p class="text mb-1">{{ formatHourlyTime(hour.date_time) }}</p>
              <img v-if="hour.icon" :src="`/static/weather_icons/${hour.icon}.svg`" :alt="hour.main"
                class="h-8 w-8 sm:h-10 sm:w-10 mx-auto mb-1 weather-icon" />
              <p class="font-bold text-base sm:text-lg">{{ hour.temp.toFixed(1) }}°</p>
              <p class="text-sm opacity-70 truncate">{{ translateWeatherCondition(hour) }}</p>

              <div
                v-if="hour.precipitation_probability !== undefined || hour.precipitation !== undefined"
                class="mt-2 sm:mt-3 space-y-2">
                <p v-if="hour.precipitation_probability !== undefined"
                  class="text-sm sm:text-base flex items-center justify-center gap-1">
                  <img :src="raindropIconUrl" alt="Raindrop" class="h-10 w-10 weather-icon" />
                  {{ hour.precipitation_probability.toFixed(0) }}%
                </p>
                <p v-if="hour.precipitation !== undefined"
                  class="text-sm sm:text-base flex items-center justify-center gap-1">
                  <img :src="showersIconUrl" alt="Showers" class="h-10 w-10 weather-icon" />
                  {{ hour.precipitation.toFixed(1) }}mm
                </p>
                <div v-if="hour.wind_speed !== undefined || hour.wind_deg !== undefined">
                  <p class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <svg v-if="hour.wind_deg !== undefined" class="h-6 w-6 weather-icon"
                      aria-hidden="true"
                      :style="{ transform: `rotate(${((hour.wind_deg ?? 0) + 180) % 360}deg)`, transformOrigin: 'center' }">
                      <use :href="windDegIconUrl" fill="currentColor" />
                    </svg>
                    {{ formatWind(hour.wind_speed, hour.wind_deg) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- details moved to main current weather view -->
      </div>

      <!-- No data message -->
      <div v-if="!forecastData || forecastData.length === 0" class="text-center py-8 opacity-70">
        <p>{{ 'No forecast data available' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import type { ForecastData, HourlyWeatherData } from '../composables/useWeather'

const { t } = useTranslation()
const raindropIconUrl = '/static/weather_icons/wi-raindrops.svg'
const showersIconUrl = '/static/weather_icons/wi-showers.svg'
const windDegIconUrl = '/static/weather_icons/wi-wind-deg.svg#Layer_1'

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

const selectedDayIndex = ref(0)
const hourlyScroller = ref<HTMLElement | null>(null)

const displayedForecastData = computed(() => props.forecastData.slice(0, 7))

watch(
  () => displayedForecastData.value.length,
  (length) => {
    if (length === 0) {
      selectedDayIndex.value = 0
      return
    }

    if (selectedDayIndex.value > length - 1) {
      selectedDayIndex.value = 0
    }
  },
  { immediate: true }
)

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
  const dayIndex = selectedDayIndex.value

  // Add all daytime hours from selected day
  if (props.daytimeHourlyData && props.daytimeHourlyData.length > dayIndex) {
    allHours.push(...(props.daytimeHourlyData[dayIndex] || []))
  }

  // Add all nighttime hours from selected day
  if (props.nighttimeHourlyData && props.nighttimeHourlyData.length > dayIndex) {
    allHours.push(...(props.nighttimeHourlyData[dayIndex] || []))
  }

  // Sort by date_time chronologically
  return allHours.sort((a, b) => {
    return new Date(a.date_time).getTime() - new Date(b.date_time).getTime()
  })
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
  const parseTimeString = (timeStr: string): Date => {
    const parsedDateTime = new Date(timeStr)
    if (!Number.isNaN(parsedDateTime.getTime())) {
      return parsedDateTime
    }

    const parts = timeStr.split(':').map(Number)
    const hours = parts[0] || 0
    const minutes = parts[1] || 0
    const seconds = parts[2] || 0
    const date = new Date()
    date.setHours(hours, minutes, seconds, 0)
    return date
  }

  const date = parseTimeString(dateString)
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

function getHourFromDateString(dateString: string): number {
  const parseTimeString = (timeStr: string): Date => {
    const parsedDateTime = new Date(timeStr)
    if (!Number.isNaN(parsedDateTime.getTime())) {
      return parsedDateTime
    }

    const parts = timeStr.split(':').map(Number)
    const hours = parts[0] || 0
    const minutes = parts[1] || 0
    const seconds = parts[2] || 0
    const date = new Date()
    date.setHours(hours, minutes, seconds, 0)
    return date
  }

  return parseTimeString(dateString).getHours()
}

function formatWind(speed: number | undefined, deg: number | undefined): string {
  if (speed === undefined || speed === null) return '-'
  // Convert m/s to km/h for display (show speed only)
  return `${(Number(speed) * 3.6).toFixed(1)} km/h`
}

async function selectDay(index: number): Promise<void> {
  selectedDayIndex.value = index
  await nextTick()
  scrollHourlyToTargetHour(index)
}

function scrollHourlyToTargetHour(index: number): void {
  const scroller = hourlyScroller.value
  if (!scroller) {
    return
  }

  const cards = Array.from(scroller.querySelectorAll<HTMLElement>('.hourly-card'))
  if (cards.length === 0) {
    return
  }

  // Use current hour for the first day (index 0, usually today), otherwise 6 AM
  const targetHour = index === 0 ? new Date().getHours() : 6

  let target = cards.find((card) => Number(card.dataset.hour) === targetHour)
  if (!target) {
    target = cards.find((card) => Number(card.dataset.hour) > targetHour) || cards[0]
  }

  if (!target) {
    return
  }

  target.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' })
}
</script>
