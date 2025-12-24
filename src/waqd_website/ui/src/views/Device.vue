<template>
  <div class="container mx-auto p-8">
    <!-- Back button and device header -->
    <div class="mb-8">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'

const router = useRouter()
const route = useRoute()
const { t } = useTranslation()

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

onMounted(async () => {
  deviceDbId.value = route.params.id as string

  // Load device info first
  await loadDeviceInfo()

  // Only connect if we successfully loaded the device
  if (deviceId.value) {
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
  } else if (messageType === 'pong') {
    // Heartbeat response
    console.log('Heartbeat acknowledged')
  } else if (messageType === 'device_status') {
    // Device status update
    isConnected.value = message.status === 'online'
  }
}

function showHistory(sensorType: string) {
  // TODO: Implement history modal/view
  console.log('Show history for:', sensorType)
  // Could open a modal or navigate to a history page
}

function goBack() {
  router.push('/devices')
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
