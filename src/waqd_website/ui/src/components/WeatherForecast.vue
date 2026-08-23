<template>
  <div class="card bg-base-100 shadow-xl min-w-0">
    <div class="card-body p-2.5 sm:p-6 min-w-0">
      <h2 class="card-title text-base sm:text-lg">{{ title }}</h2>

      <!-- 7-Day Forecast Section -->
      <div v-if="forecastData && forecastData.length > 0" class="mb-2 sm:mb-6">
        <h3 class="font-semibold text-sm sm:text-base mb-1.5 sm:mb-4">{{
          t('weekly_weather_forecast')
        }}</h3>
        <div ref="forecastScroller" class="overflow-x-auto w-full max-w-full -mx-2 px-2">
          <div class="flex gap-1.5 sm:gap-3 lg:gap-4 pt-1 pb-2 min-w-max">
            <button v-for="(day, index) in displayedForecastData" :key="index" type="button"
              :data-day-index="index"
              class="card bg-base-200 shadow-md text-left transition-all duration-150 flex-shrink-0 min-w-[118px] sm:min-w-[170px]"
              :class="selectedDayIndex === index ? 'ring-2 ring-primary bg-base-300' : 'hover:bg-base-300/70'"
              @click="selectDay(index)">
              <div class="card-body p-1.5 sm:p-3 lg:p-4 text-center">
                <!-- Day label -->
                <h3 class="font-bold text-sm sm:text-base mb-0.5 sm:mb-2">
                  {{ formatForecastDate(day.date_time) }}
                </h3>

                <!-- Weather icon -->
                <img v-if="day.icon" :src="`/static/weather_icons/${day.icon}.svg`" :alt="day.main"
                  class="h-8 w-8 sm:h-12 sm:w-12 lg:h-14 lg:w-14 mx-auto mb-0.5 sm:mb-2 weather-icon" />

                <!-- Weather condition -->
                <p class="text-sm opacity-70 mb-0.5 sm:mb-2 line-clamp-2">{{
                  translateWeatherCondition(day) }}</p>

                <!-- Day temperature -->
                <div
                  class="mb-0.5 mx-auto flex w-fit items-center justify-center gap-1 rounded-full bg-warning/15 px-2.5 py-0.5">
                  <img :src="daySunnyIconUrl" :alt="t('day')"
                    class="h-4 w-4 sm:h-5 sm:w-5 weather-icon" />
                  <span class="font-bold text-sm sm:text-base">{{ day.temp_min.toFixed(0) }}° / {{
                    day.temp_max.toFixed(0) }}°</span>
                </div>

                <!-- Night temperature -->
                <div
                  class="mb-0.5 sm:mb-2 mx-auto flex w-fit items-center justify-center gap-1 rounded-full bg-info/15 px-2.5 py-0.5">
                  <img :src="nightClearIconUrl" :alt="t('night')"
                    class="h-4 w-4 sm:h-5 sm:w-5 weather-icon" />
                  <span class="text-sm sm:text-base">{{ day.temp_night_min.toFixed(0) }}° / {{
                    day.temp_night_max.toFixed(0) }}°</span>
                </div>

                <!-- Precipitation probability -->
                <div
                  v-if="day.precipitation_probability_max !== undefined || day.precipitation !== undefined"
                  class="space-y-0.5">
                  <p v-if="day.precipitation_probability_max !== undefined"
                    class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <img :src="raindropIconUrl" alt="Raindrop"
                      class="h-6 w-6 sm:h-10 sm:w-10 weather-icon" />
                    {{ day.precipitation_probability_max.toFixed(0) }}%
                  </p>
                  <div v-if="day.precipitation_probability_max !== undefined"
                    class="h-1 w-full overflow-hidden rounded-full bg-base-300">
                    <div class="h-full rounded-full bg-info transition-all duration-300"
                      :style="{ width: `${Math.min(100, Math.max(0, day.precipitation_probability_max))}%` }">
                    </div>
                  </div>
                  <p v-if="day.precipitation !== undefined"
                    class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <img :src="showersIconUrl" alt="Showers"
                      class="h-6 w-6 sm:h-10 sm:w-10 weather-icon" />
                    {{ day.precipitation.toFixed(1) }}mm
                  </p>
                </div>
                <!-- Daily wind display (moved from details) -->
                <div v-if="day.wind_speed !== undefined || day.wind_deg !== undefined"
                  class="mt-1 sm:mt-3 space-y-1">
                  <p class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <svg v-if="day.wind_deg !== undefined"
                      class="h-5 w-5 sm:h-8 sm:w-8 weather-icon" aria-hidden="true"
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

        <!-- Selected day detail band -->
        <div v-if="selectedDay"
          class="mt-2 sm:mt-3 flex flex-wrap items-center gap-3 sm:gap-6 rounded-box bg-base-200 p-3 sm:p-4">
          <img v-if="selectedDay.icon" :src="`/static/weather_icons/${selectedDay.icon}.svg`"
            :alt="selectedDay.main" class="h-10 w-10 sm:h-14 sm:w-14 weather-icon" />
          <div class="min-w-0">
            <p class="font-bold text-sm sm:text-base">{{ formatForecastDate(selectedDay.date_time)
            }}</p>
            <p class="text-xs sm:text-sm opacity-70">{{ translateWeatherCondition(selectedDay) }}
            </p>
          </div>
          <div class="ms-auto flex flex-wrap items-center gap-x-4 gap-y-1 text-xs sm:text-sm">
            <span class="flex items-center gap-1">
              <svg class="h-4 w-4 sm:h-5 sm:w-5 text-warning" aria-hidden="true">
                <use :href="sunriseIconUrl" fill="currentColor" />
              </svg>
              {{ formatDayTime(selectedDay.sunrise) }}
            </span>
            <span class="flex items-center gap-1">
              <svg class="h-4 w-4 sm:h-5 sm:w-5 text-orange-400" aria-hidden="true">
                <use :href="sunsetIconUrl" fill="currentColor" />
              </svg>
              {{ formatDayTime(selectedDay.sunset) }}
            </span>
            <span v-if="selectedDay.wind_speed !== undefined" class="flex items-center gap-1">
              <svg class="h-4 w-4 sm:h-5 sm:w-5 text-accent" aria-hidden="true"
                :style="{ transform: `rotate(${((selectedDay.wind_deg ?? 0) + 180) % 360}deg)`, transformOrigin: 'center' }">
                <use :href="windDegIconUrl" fill="currentColor" />
              </svg>
              {{ formatWind(selectedDay.wind_speed, selectedDay.wind_deg) }}
            </span>
            <span v-if="selectedDay.precipitation !== undefined" class="flex items-center gap-1">
              <img :src="showersIconUrl" :alt="t('weather_rain')"
                class="h-4 w-4 sm:h-5 sm:w-5 weather-icon" />
              {{ selectedDay.precipitation.toFixed(1) }}mm
            </span>
          </div>
        </div>
      </div>
      <div v-if="hasHourlyData" class="mt-4 sm:mt-6">
        <h3 class="font-semibold text-sm sm:text-base mb-3 sm:mb-4">
          {{ t('hourly_forecast') }} ({{ mergedHourlyData.length }} {{ t('hours') }})
        </h3>

        <!-- Temperature curve + precipitation bars for the selected day -->
        <div ref="hourlyChartContainer" class="w-full h-36 sm:h-44 mb-2"></div>

        <!-- Hourly data display in a single row -->
        <div ref="hourlyScroller" class="overflow-x-auto w-full max-w-full -mx-2 px-2">
          <div class="flex gap-1.5 sm:gap-2 pt-1 pb-2 min-w-max">
            <div v-for="(hour, index) in mergedHourlyData" :key="index"
              class="hourly-card flex-shrink-0 card bg-base-200 p-1.5 sm:p-3 min-w-[74px] sm:min-w-[110px] text-center"
              :data-hour="getHourFromDateString(hour.date_time)">
              <p class="text mb-0.5">{{ formatHourlyTime(hour.date_time) }}</p>
              <img v-if="hour.icon" :src="`/static/weather_icons/${hour.icon}.svg`" :alt="hour.main"
                class="h-6 w-6 sm:h-10 sm:w-10 mx-auto mb-0.5 weather-icon" />
              <p class="font-bold text-sm sm:text-lg">{{ hour.temp.toFixed(1) }}°</p>
              <p class="text-sm opacity-70 line-clamp-2">{{ translateWeatherCondition(hour) }}</p>

              <div
                v-if="hour.precipitation_probability !== undefined || hour.precipitation !== undefined"
                class="mt-1 sm:mt-3 space-y-1 sm:space-y-2">
                <p v-if="hour.precipitation_probability !== undefined"
                  class="text-sm sm:text-base flex items-center justify-center gap-1">
                  <img :src="raindropIconUrl" alt="Raindrop"
                    class="h-6 w-6 sm:h-10 sm:w-10 weather-icon" />
                  {{ hour.precipitation_probability.toFixed(0) }}%
                </p>
                <div v-if="hour.precipitation_probability !== undefined"
                  class="h-1 w-full overflow-hidden rounded-full bg-base-300">
                  <div class="h-full rounded-full bg-info transition-all duration-300"
                    :style="{ width: `${Math.min(100, Math.max(0, hour.precipitation_probability))}%` }">
                  </div>
                </div>
                <p v-if="hour.precipitation !== undefined"
                  class="text-sm sm:text-base flex items-center justify-center gap-1">
                  <img :src="showersIconUrl" alt="Showers"
                    class="h-6 w-6 sm:h-10 sm:w-10 weather-icon" />
                  {{ hour.precipitation.toFixed(1) }}mm
                </p>
                <div v-if="hour.wind_speed !== undefined || hour.wind_deg !== undefined">
                  <p class="text-sm sm:text-base flex items-center justify-center gap-1">
                    <svg v-if="hour.wind_deg !== undefined"
                      class="h-5 w-5 sm:h-6 sm:w-6 weather-icon" aria-hidden="true"
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
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import type { ForecastData, HourlyWeatherData } from '../composables/useWeather'
import Highcharts from 'highcharts'

const { t, locale } = useTranslation()
const raindropIconUrl = '/static/weather_icons/wi-raindrops.svg'
const showersIconUrl = '/static/weather_icons/wi-showers.svg'
const windDegIconUrl = '/static/weather_icons/wi-wind-deg.svg#Layer_1'
const daySunnyIconUrl = '/static/weather_icons/wi-day-sunny.svg'
const nightClearIconUrl = '/static/weather_icons/wi-night-clear.svg'
const sunriseIconUrl = '/static/weather_icons/wi-sunrise.svg#Layer_1'
const sunsetIconUrl = '/static/weather_icons/wi-sunset.svg#Layer_1'

interface Props {
  title?: string
  forecastData?: ForecastData[]
  daytimeHourlyData?: HourlyWeatherData[][]
  nighttimeHourlyData?: HourlyWeatherData[][]
  initialDayIndex?: number
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Weather Forecast',
  forecastData: () => [],
  daytimeHourlyData: () => [],
  nighttimeHourlyData: () => [],
  initialDayIndex: 0
})

const selectedDayIndex = ref(props.initialDayIndex)

watch(
  () => props.initialDayIndex,
  (idx) => {
    if (idx !== undefined && idx >= 0 && displayedForecastData.value.length > 0) {
      selectDay(Math.min(idx, displayedForecastData.value.length - 1))
    }
  }
)
const hourlyScroller = ref<HTMLElement | null>(null)
const forecastScroller = ref<HTMLElement | null>(null)

const displayedForecastData = computed(() => props.forecastData.slice(0, 7))

// When forecast data loads/changes, restore the intended day (initialDayIndex) instead of always falling back to 0
watch(
  () => displayedForecastData.value.length,
  async (length) => {
    if (length === 0) {
      selectedDayIndex.value = 0
      return
    }
    const target = props.initialDayIndex ?? 0
    selectedDayIndex.value = target < length ? target : 0
    await nextTick()
    scrollForecastDayIntoView(selectedDayIndex.value)
    scrollHourlyToTargetHour(selectedDayIndex.value)
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

// The day currently selected in the 7-day scroller (drives detail band + hourly data)
const selectedDay = computed(() => displayedForecastData.value[selectedDayIndex.value])

function formatDayTime(timeStr: string): string {
  const parsed = new Date(timeStr)
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  const parts = (timeStr || '').split(':').map(Number)
  const date = new Date()
  date.setHours(parts[0] || 0, parts[1] || 0, parts[2] || 0, 0)
  return date.toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit', hour12: false })
}

// --- Hourly temperature/precipitation chart ---
const hourlyChartContainer = ref<HTMLElement | null>(null)
let hourlyChart: Highcharts.Chart | null = null

function renderHourlyChart(): void {
  const container = hourlyChartContainer.value
  if (!container) return

  if (hourlyChart) {
    hourlyChart.destroy()
    hourlyChart = null
  }

  const hours = mergedHourlyData.value
  if (hours.length === 0) return

  // Theme-aware colors, same approach as the sensor history chart
  const contentColor = getComputedStyle(document.documentElement).getPropertyValue('--color-base-content').trim()
  const axisLabelColor = contentColor ? `color-mix(in srgb, ${contentColor} 75%, transparent)` : 'currentColor'
  const gridColor = contentColor ? `color-mix(in srgb, ${contentColor} 15%, transparent)` : 'rgba(128, 128, 128, 0.15)'

  const tempData = hours.map(h => [new Date(h.date_time).getTime(), h.temp] as [number, number])
  const precipData = hours.map(h => [new Date(h.date_time).getTime(), h.precipitation ?? 0] as [number, number])

  // Soft temperature window: data range ± 2 °C so small changes stay visible
  const temps = hours.map(h => h.temp)
  const tempSoftMin = Math.min(...temps) - 2
  const tempSoftMax = Math.max(...temps) + 2

  hourlyChart = (Highcharts as any).chart(container, {
    time: { useUTC: false },
    chart: {
      backgroundColor: 'transparent',
      style: { fontFamily: 'inherit' },
      spacing: [4, 0, 4, 12]
    },
    title: { text: undefined },
    xAxis: {
      type: 'datetime',
      dateTimeLabelFormats: {
        hour: '%H:%M',
        minute: '%H:%M'
      },
      labels: { style: { fontSize: '11px', color: axisLabelColor } },
      lineColor: gridColor,
      tickColor: gridColor
    },
    yAxis: [
      {
        // Temperature (left)
        softMin: tempSoftMin,
        softMax: tempSoftMax,
        startOnTick: false,
        endOnTick: false,
        title: { text: undefined },
        labels: { format: '{value}°', style: { fontSize: '11px', color: axisLabelColor } },
        gridLineColor: gridColor
      },
      {
        // Precipitation (right)
        min: 0,
        title: { text: undefined },
        labels: { format: '{value}mm', style: { fontSize: '11px', color: axisLabelColor } },
        opposite: true,
        gridLineWidth: 0
      }
    ],
    legend: { enabled: false },
    tooltip: {
      shared: true,
      xDateFormat: '%H:%M',
      style: { fontSize: '12px' }
    },
    plotOptions: {
      series: {
        marker: { enabled: false },
        animation: false
      }
    },
    series: [
      {
        type: 'spline',
        name: t('temperature'),
        data: tempData,
        color: 'rgb(245, 158, 11)',
        lineWidth: 2,
        yAxis: 0,
        tooltip: { valueSuffix: '°C', valueDecimals: 1 }
      },
      {
        type: 'column',
        name: t('weather_rain'),
        data: precipData,
        color: 'rgba(54, 162, 235, 0.45)',
        borderWidth: 0,
        yAxis: 1,
        tooltip: { valueSuffix: ' mm', valueDecimals: 1 }
      }
    ],
    credits: { enabled: false }
  })
}

watch(mergedHourlyData, async () => {
  await nextTick()
  renderHourlyChart()
})

onMounted(() => {
  renderHourlyChart()
})

onUnmounted(() => {
  if (hourlyChart) {
    hourlyChart.destroy()
    hourlyChart = null
  }
})

// Scroll only the horizontal scroller itself (never scrollIntoView, which can also nudge page/vertical scroll).
function scrollToCardStart(scroller: HTMLElement, card: HTMLElement): void {
  const scrollerRect = scroller.getBoundingClientRect()
  const cardRect = card.getBoundingClientRect()
  const paddingLeft = parseFloat(getComputedStyle(scroller).paddingLeft)
  const targetLeft = Math.max(
    0,
    Math.min(
      scroller.scrollLeft + cardRect.left - scrollerRect.left - paddingLeft,
      scroller.scrollWidth - scroller.clientWidth
    )
  )
  scroller.scrollTo({ left: targetLeft, behavior: 'smooth' })
}

function scrollForecastDayIntoView(index: number): void {
  if (index === 0) return

  const scroller = forecastScroller.value
  if (!scroller) return
  const card = scroller.querySelector<HTMLElement>(`[data-day-index="${index}"]`)
  if (card) {
    scrollToCardStart(scroller, card)
  }
}

async function selectDay(index: number): Promise<void> {
  selectedDayIndex.value = index
  await nextTick()
  scrollForecastDayIntoView(index)
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

  scrollToCardStart(scroller, target)
}
</script>
