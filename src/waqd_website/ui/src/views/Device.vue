<template>
  <div class="container mx-auto p-8">
    <!-- Back button and device header with weather background -->
    <div class="mb-8 -mx-8 -mt-8 p-8 rounded-b-lg overflow-hidden transition-all duration-500" :style="weatherBackgroundStyle">
      <div class="bg-base-100/80 backdrop-blur-sm p-6 rounded-lg">
      <button @click="goBack" class="btn btn-ghost btn-sm mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20"
          fill="currentColor">
          <path fill-rule="evenodd"
            d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
            clip-rule="evenodd" />
        </svg>
        {{ t('back_to_devices') }}
      </button>

      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-4xl font-bold mb-2">{{ deviceName || t('loading') }}</h1>
          <div class="flex items-center gap-4">
            <div class="badge" :class="isConnected ? 'badge-success' : 'badge-error'">
              {{ isConnected ? t('online') : t('offline') }}
            </div>
            <span class="text-sm opacity-70 font-mono">{{ deviceId }}</span>
          </div>
        </div>
        <div v-if="lastUpdated" class="text-sm opacity-70">
          {{ t('last_updated') }}: {{ formatTime(lastUpdated) }}
        </div>
      </div>

      <!-- Weather Info Banner (only if device is connected and has weather data) -->
      <div v-if="weatherData && isConnected" class="mt-6">
        <div class="flex items-center gap-4 w-full bg-base-100/60 backdrop-blur-sm rounded-lg p-4">
          <img 
            v-if="weatherData.icon" 
            :src="`/static/weather_icons/${weatherData.icon}.svg`" 
            alt="Weather icon"
            class="h-16 w-16 brightness-0 invert"
          />
          <div class="flex-1">
            <h3 class="font-bold text-lg text-white">{{ weatherData.main }}</h3>
            <p class="text-sm text-white/70">{{ deviceLocation || t('current_weather') }}</p>
          </div>
          <div class="text-right">
            <p class="text-3xl font-bold text-white">{{ weatherData.temp.toFixed(1) }}°C</p>
            <p class="text-sm text-white/70">{{ t('outdoor') }}</p>
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- Connection Error -->
    <div v-if="connectionError" class="alert alert-error mb-8">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24"
        stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{{ connectionError }}</span>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center min-h-[50vh]">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Interior Sensor Data Grid -->
    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <!-- Temperature Card -->
      <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow cursor-pointer"
        @click="showHistory('temperature')">
        <div class="card-body">
          <div class="flex justify-between items-start">
            <div>
              <h2 class="card-title text-lg opacity-70">{{ t('temperature') }}</h2>
              <p class="text-6xl font-bold tracking-tighter mt-2">
                {{ sensorData.temp ?? '--' }}
                <a v-if="sensorData.temp" class="opacity-70 mt-1">°C</a>
              </p>
            </div>
            <div class="stat-figure">
              <svg viewBox="0 0 24 24" class="h-16 w-16 opacity-50">
                <use :href="thermometerIconUrl" fill="currentColor" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Humidity Card -->
      <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow cursor-pointer"
        @click="showHistory('humidity')">
        <div class="card-body">
          <div class="flex justify-between items-start">
            <div>
              <h2 class="card-title text-lg opacity-70">{{ t('humidity') }}</h2>
              <p class="text-6xl font-bold mt-2">
                {{ sensorData.hum ?? '--' }}
                <a v-if="sensorData.hum" class="opacity-70">%</a>
              </p>
            </div>
            <div class="stat-figure">
              <svg viewBox="0 0 24 24" class="h-16 w-16 opacity-50">
                <use :href="humidityIconUrl" fill="currentColor" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- CO2 Card -->
      <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow cursor-pointer"
        @click="showHistory('co2')">
        <div class="card-body">
          <div class="flex justify-between items-start">
            <div>
              <h2 class="card-title text-lg opacity-70">{{ t('co2') }}</h2>
              <p class="text-6xl font-bold mt-2" :class="co2ColorClass">
                {{ sensorData.co2 ?? '--' }}
                <a v-if="sensorData.co2" class="opacity-70 mt-1">ppm</a>
              </p>
            </div>
            <div class="stat-figure">
              <svg viewBox="0 0 26 26" class="h-16 w-16 opacity-50">
                <use :href="co2IconUrl" fill="currentColor" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Pressure Card -->
      <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow cursor-pointer"
        @click="showHistory('pressure')">
        <div class="card-body">
          <div class="flex justify-between items-start">
            <div>
              <h2 class="card-title text-lg opacity-70">{{ t('pressure') }}</h2>
              <p class="text-6xl font-bold mt-2">
                {{ sensorData.baro ?? '--' }}
                <a v-if="sensorData.baro" class="opacity-70 mt-1">hPa</a>
              </p>
            </div>
            <div class="stat-figure">
              <svg viewBox="0 0 24 24" class="h-16 w-16 opacity-50">
                <use :href="barometerIconUrl" fill="currentColor" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Weather Forecast Component -->
    <WeatherForecast 
      v-if="isConnected"
      :title="t('weather_forecast') || 'Weather Forecast'"
      :forecastData="forecastData"
      :daytimeHourlyData="hourlyDaytimeData"
      :nighttimeHourlyData="hourlyNighttimeData"
      class="mt-8"
    />

    <!-- Device Info Section -->
    <div class="card bg-base-100 shadow-xl mt-8">
      <div class="card-body">
        <h2 class="card-title">{{ t('device_information') }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div>
            <p class="text-sm opacity-70">{{ t('device_id') }}</p>
            <p class="font-mono">{{ deviceId }}</p>
          </div>
          <div v-if="deviceLocation">
            <p class="text-sm opacity-70">{{ t('location') }}</p>
            <p>{{ deviceLocation }}</p>
          </div>
          <div v-if="lastUpdated">
            <p class="text-sm opacity-70">{{ t('last_update') }}</p>
            <p>{{ formatDateTime(lastUpdated) }}</p>
          </div>
          <div>
            <p class="text-sm opacity-70">{{ t('connection_status') }}</p>
            <p :class="isConnected ? 'text-success' : 'text-error'">
              {{ isConnected ? t('connected') : t('disconnected') }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Sensor History Modal -->
    <SensorHistoryModal ref="sensorHistoryModal" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'
import { useWeather, type WeatherData, type ForecastData, type HourlyWeatherData } from '../composables/useWeather'
import { useSensorHistory, type SensorHistoryData } from '../composables/useSensorHistory'
import WeatherForecast from '../components/WeatherForecast.vue'
import SensorHistoryModal from '../components/SensorHistoryModal.vue'

const router = useRouter()
const route = useRoute()
const { t } = useTranslation()
const { 
  getWeatherData, 
  setWeatherData, 
  getForecastData, 
  setForecastData, 
  getHourlyDaytimeData,
  getHourlyNighttimeData,
  setHourlyForecastData,
  getWeatherBackground, 
  isDay: isDayWeather 
} = useWeather()
const { setSensorHistory, getSensorHistory } = useSensorHistory()

// Static asset URLs
const thermometerIconUrl = '/static/weather_icons/wi-thermometer_full.svg#Layer_1'
const humidityIconUrl = '/static/weather_icons/wi-humidity.svg#Layer_1'
const co2IconUrl = '/static/general_icons/aq_indoor.svg#main'
const barometerIconUrl = '/static/weather_icons/wi-barometer.svg#Layer_1'

const deviceDbId = ref('')  // Database ID from route
const deviceId = ref('')  // Actual device_id (MAC address)
const deviceName = ref('')
const deviceLocation = ref('')
const loading = ref(true)
const isConnected = ref(false)
const connectionError = ref('')
const lastUpdated = ref<Date | null>(null)

interface SensorData {
  temp?: number
  hum?: number
  baro?: number
  co2?: number
  tvoc?: number
  dust?: number
  light?: number
  timestamp?: number
}

const sensorData = ref<SensorData>({})
const weatherData = ref<WeatherData | null>(null)
const forecastData = ref<ForecastData[]>([])
const hourlyDaytimeData = ref<HourlyWeatherData[][]>([])
const hourlyNighttimeData = ref<HourlyWeatherData[][]>([])

const sensorHistoryModal = ref<InstanceType<typeof SensorHistoryModal> | null>(null)

let ws: WebSocket | null = null
let reconnectTimeout: number | null = null
let heartbeatInterval: number | null = null

// Computed property for CO2 color coding
const co2ColorClass = computed(() => {
  const co2Value = sensorData.value.co2
  if (!co2Value) return ''

  if (co2Value < 800) return 'text-success'
  if (co2Value < 1200) return 'text-warning'
  return 'text-error'
})

// Computed property for weather background
const weatherBackgroundStyle = computed(() => {
  if (!deviceId.value) return {}
  return getWeatherBackground(deviceId.value)
})

onMounted(async () => {
  deviceDbId.value = route.params.id as string

  // Load device info first
  await loadDeviceInfo()

  // Load weather data from composable if available
  if (deviceId.value) {
    const storedWeather = getWeatherData(deviceId.value)
    if (storedWeather) {
      weatherData.value = storedWeather
    }
    const storedForecast = getForecastData(deviceId.value)
    if (storedForecast) {
      forecastData.value = storedForecast
    }
    const storedHourlyDaytime = getHourlyDaytimeData(deviceId.value)
    if (storedHourlyDaytime) {
      hourlyDaytimeData.value = storedHourlyDaytime
    }
    const storedHourlyNighttime = getHourlyNighttimeData(deviceId.value)
    if (storedHourlyNighttime) {
      hourlyNighttimeData.value = storedHourlyNighttime
    }
    connectWebSocket()
  }
})

onUnmounted(() => {
  disconnectWebSocket()
})

async function loadDeviceInfo() {
  try {
    const response = await fetch('/api/user/devices', {
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error('Failed to load device info')
    }

    const data = await response.json()
    const device = data.devices?.find((d: any) => d.id.toString() === deviceDbId.value)

    if (device) {
      deviceId.value = device.device_id  // This is the actual device_id (MAC address)
      deviceName.value = device.name || device.device_id
      deviceLocation.value = device.location || ''
    } else {
      connectionError.value = t('device_not_found') || 'Device not found'
    }
  } catch (error) {
    console.error('Error loading device info:', error)
    connectionError.value = t('error_loading_device') || 'Failed to load device information'
  } finally {
    loading.value = false
  }
}

function connectWebSocket() {
  if (ws) return

  // Don't connect if we don't have a valid device_id
  if (!deviceId.value) {
    console.error('Cannot connect WebSocket: no device_id')
    connectionError.value = t('device_not_found') || 'Device not found'
    return
  }

  // Construct WebSocket URL - connect directly to device stream
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/user/device/${deviceId.value}`

  console.log('Connecting to WebSocket:', wsUrl)

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected to device:', deviceId.value)
      isConnected.value = true
      connectionError.value = ''

      // Start heartbeat
      startHeartbeat()
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleWebSocketMessage(message)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      connectionError.value = t('connection_error') || 'Connection error occurred'
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      isConnected.value = false
      ws = null

      // Attempt to reconnect after 5 seconds
      reconnectTimeout = window.setTimeout(() => {
        console.log('Attempting to reconnect...')
        connectWebSocket()
      }, 5000)
    }
  } catch (error) {
    console.error('Error creating WebSocket:', error)
    connectionError.value = t('connection_error') || 'Failed to connect to device'
  }
}

function disconnectWebSocket() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval)
    heartbeatInterval = null
  }

  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }

  if (ws) {
    ws.close()
    ws = null
  }
}

function startHeartbeat() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval)
  }

  heartbeatInterval = window.setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }, 30000) // Send heartbeat every 30 seconds
}

function handleWebSocketMessage(message: any) {
  const messageType = message.type

  if (messageType === 'sensor_data') {
    // Update sensor data - convert strings to numbers, handle "N/A"
    const data = message.data

    const parseValue = (value: any): number | undefined => {
      if (value === undefined || value === null || value === 'N/A') {
        return undefined
      }
      const parsed = parseFloat(value)
      return isNaN(parsed) ? undefined : parsed
    }

    sensorData.value = {
      temp: parseValue(data.temp) !== undefined ? parseFloat(parseValue(data.temp)!.toFixed(1)) : undefined,
      hum: parseValue(data.hum) !== undefined ? parseFloat(parseValue(data.hum)!.toFixed(1)) : undefined,
      co2: parseValue(data.co2) !== undefined ? Math.round(parseValue(data.co2)!) : undefined,
      baro: parseValue(data.baro) !== undefined ? Math.round(parseValue(data.baro)!) : undefined,
      timestamp: message.timestamp
    }
    lastUpdated.value = new Date()
  } else if (messageType === 'weather_data') {
    // Update weather data for background
    weatherData.value = message.data
    // Store in composable for reuse
    if (deviceId.value) {
      setWeatherData(deviceId.value, message.data)
    }
    console.log('Weather data received:', weatherData.value)
  } else if (messageType === 'forecast_data') {
    // Update forecast data
    forecastData.value = message.data
    // Store in composable for reuse
    if (deviceId.value) {
      setForecastData(deviceId.value, message.data)
    }
    console.log('Forecast data received:', forecastData.value)
  } else if (messageType === 'hourly_forecast_data') {
    // Update hourly forecast data
    hourlyDaytimeData.value = message.daytime || []
    hourlyNighttimeData.value = message.nighttime || []
    // Store in composable for reuse
    if (deviceId.value) {
      setHourlyForecastData(deviceId.value, message.daytime || [], message.nighttime || [])
    }
    console.log('Hourly forecast data received - daytime:', hourlyDaytimeData.value.length, 'nighttime:', hourlyNighttimeData.value.length)
  } else if (messageType === 'sensor_history_data') {
    // Update sensor history data
    const historyData = message.data as SensorHistoryData
    if (deviceId.value) {
      setSensorHistory(deviceId.value, historyData)
    }
    console.log('Sensor history data received:', Object.keys(historyData).length, 'sensor types')
  } else if (messageType === 'pong') {
    // Heartbeat response
    console.log('Heartbeat acknowledged')
  } else if (messageType === 'device_status') {
    // Device status update
    isConnected.value = message.status === 'online'
  }
}

function showHistory(sensorType: string) {
  if (!sensorHistoryModal.value || !deviceId.value) return
  
  const sensorConfigs: Record<string, any> = {
    'temperature': {
      deviceId: deviceId.value,
      sensorType: 'temperature',
      sensorLocation: 'interior',
      title: t('interior_temperature_history') || 'Interior Temperature History',
      label: t('temperature') || 'Temperature',
      unit: '°C',
      color: 'rgb(255, 99, 132)',
      backgroundColor: 'rgba(255, 99, 132, 0.1)'
    },
    'humidity': {
      deviceId: deviceId.value,
      sensorType: 'humidity',
      sensorLocation: 'interior',
      title: t('interior_humidity_history') || 'Interior Humidity History',
      label: t('humidity') || 'Humidity',
      unit: '%',
      color: 'rgb(54, 162, 235)',
      backgroundColor: 'rgba(54, 162, 235, 0.1)'
    },
    'co2': {
      deviceId: deviceId.value,
      sensorType: 'co2',
      sensorLocation: 'interior',
      title: t('co2_history') || 'CO₂ History',
      label: t('co2') || 'CO₂',
      unit: ' ppm',
      color: 'rgb(75, 192, 75)',
      backgroundColor: 'rgba(75, 192, 75, 0.1)'
    },
    'pressure': {
      deviceId: deviceId.value,
      sensorType: 'pressure',
      sensorLocation: 'interior',
      title: t('pressure_history') || 'Pressure History',
      label: t('pressure') || 'Pressure',
      unit: ' hPa',
      color: 'rgb(153, 102, 255)',
      backgroundColor: 'rgba(153, 102, 255, 0.1)'
    }
  }
  
  const config = sensorConfigs[sensorType]
  if (config) {
    sensorHistoryModal.value.show(config)
  }
}

function goBack() {
  router.push('/rest/devices')
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString()
}

function formatDateTime(date: Date): string {
  return date.toLocaleString()
}
</script>

<style scoped>
/* Add any component-specific styles here */
</style>
