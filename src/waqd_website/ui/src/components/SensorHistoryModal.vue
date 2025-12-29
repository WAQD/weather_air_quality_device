<template>
  <dialog ref="modalRef" class="modal">
    <div class="modal-box w-11/12 max-w-7xl h-5/6 max-h-screen">
      <form method="dialog">
        <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
      </form>
      
      <div class="flex justify-between items-center mb-4">
        <h3 class="font-bold text-2xl">{{ modalTitle }}</h3>
        <select v-model="selectedTimeRange" class="select select-bordered" @change="fetchData">
          <option value="6">{{ t('last_6_hours') || 'Last 6 hours' }}</option>
          <option value="12">{{ t('last_12_hours') || 'Last 12 hours' }}</option>
          <option value="24">{{ t('last_24_hours') || 'Last 24 hours' }}</option>
          <option value="48">{{ t('last_48_hours') || 'Last 48 hours' }}</option>
          <option value="168">{{ t('last_7_days') || 'Last 7 days' }}</option>
          <option value="720">{{ t('last_30_days') || 'Last 30 days' }}</option>
        </select>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center h-96">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="alert alert-error">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{{ error }}</span>
      </div>

      <!-- Chart -->
      <div v-else class="w-full" style="height: calc(100% - 80px);">
        <canvas ref="chartCanvas"></canvas>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button>close</button>
    </form>
  </dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import { useSensorHistory, type SensorHistoryData } from '../composables/useSensorHistory'
import { Chart, registerables } from 'chart.js'

// Register Chart.js components
Chart.register(...registerables)

const { t } = useTranslation()
const { getSensorHistory } = useSensorHistory()

interface SensorDataPoint {
  timestamp: string
  value: number
}

interface SensorConfig {
  deviceId: string
  sensorType: 'temperature' | 'humidity' | 'co2' | 'pressure'
  sensorLocation: 'interior' | 'exterior'
  title: string
  label: string
  unit: string
  color: string
  backgroundColor: string
}

const modalRef = ref<HTMLDialogElement | null>(null)
const chartCanvas = ref<HTMLCanvasElement | null>(null)
const selectedTimeRange = ref(12)
const loading = ref(false)
const error = ref('')
const modalTitle = ref('')

let chart: Chart | null = null
let currentConfig: SensorConfig | null = null

const sensorTypeMap: Record<string, string> = {
  'temperature': 'temp_degC',
  'humidity': 'humidity_%',
  'co2': 'CO2_ppm',
  'pressure': 'pressure_hPa'
}

async function show(config: SensorConfig) {
  currentConfig = config
  modalTitle.value = config.title
  error.value = ''
  
  // Open modal
  modalRef.value?.showModal()
  
  // Wait for modal to be visible
  await nextTick()
  
  // Fetch and display data
  await fetchData()
}

async function fetchData() {
  if (!currentConfig) return
  
  loading.value = true
  error.value = ''
  
  try {
    const sensorTypeKey = sensorTypeMap[currentConfig.sensorType]
    
    // First, try to use streamed data from WebSocket
    const cachedHistory = getSensorHistory(currentConfig.deviceId)
    
    if (cachedHistory && cachedHistory[sensorTypeKey as keyof SensorHistoryData]) {
      // Use cached data from WebSocket
      const dataPoints = cachedHistory[sensorTypeKey as keyof SensorHistoryData]!
      
      const labels: string[] = []
      const values: number[] = []
      
      for (const point of dataPoints) {
        const date = new Date(point.timestamp)
        labels.push(formatTime(date))
        values.push(point.value)
      }
      
      // Store data for chart rendering after loading completes
      loading.value = false
      
      // Wait for DOM to update (loading spinner removed, canvas shown)
      await nextTick()
      
      // Update chart
      if (chartCanvas.value) {
        updateChart(labels, values, currentConfig)
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load sensor data'
    console.error('Error fetching sensor history:', e)
    loading.value = false
  }
}

function updateChart(labels: string[], values: number[], config: SensorConfig) {
  if (!chartCanvas.value) return
  
  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return
  
  // Destroy existing chart
  if (chart) {
    chart.destroy()
  }
  
  // Create new chart
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: config.label,
        data: values,
        borderColor: config.color,
        backgroundColor: config.backgroundColor,
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 6,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
        },
        tooltip: {
          callbacks: {
            label: function(context: any) {
              let label = context.dataset.label || ''
              if (label) {
                label += ': '
              }
              label += context.parsed.y.toFixed(1) + config.unit
              return label
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          title: {
            display: true,
            text: `${config.label} (${config.unit})`
          },
          ticks: {
            callback: function(value: any) {
              return (value as number).toFixed(1) + config.unit
            }
          }
        },
        x: {
          title: {
            display: true,
            text: t('time') || 'Time'
          },
          ticks: {
            maxRotation: 45,
            minRotation: 45
          }
        }
      }
    }
  })
}

function formatTime(date: Date): string {
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  
  // For 48 hours or more, always include the date
  if (selectedTimeRange.value >= 48) {
    const day = date.getDate().toString().padStart(2, '0')
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    return `${month}/${day}\n${hours}:${minutes}`
  }
  
  return `${hours}:${minutes}`
}

function close() {
  modalRef.value?.close()
  if (chart) {
    chart.destroy()
    chart = null
  }
}

// Expose methods to parent
defineExpose({
  show,
  close
})

onUnmounted(() => {
  if (chart) {
    chart.destroy()
  }
})
</script>

<style scoped>
/* Add any component-specific styles here */
</style>
