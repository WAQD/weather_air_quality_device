<template>
  <dialog ref="modalRef" class="modal">
    <div class="modal-box w-11/12 max-w-7xl h-5/6 max-h-screen">
      <form method="dialog">
        <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
      </form>
      
      <div class="flex justify-between items-center mb-2 mr-4">
        <h3 class="font-bold text-2xl">{{ modalTitle }}</h3>
        <select v-model="selectedTimeRange" class="select select-bordered" @change="fetchData">
          <option value="6">{{ t('history_last_6_hours') }}</option>
          <option value="12">{{ t('history_last_12_hours') }}</option>
          <option value="24">{{ t('history_last_24_hours') }}</option>
          <option value="48">{{ t('history_last_48_hours') }}</option>
          <option value="168">{{ t('history_last_7_days')}}</option>
          <option value="720">{{ t('history_last_30_days') }}</option>
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
      <div v-else class="w-full" style="height: calc(100% - 60px);">
        <div ref="chartContainer" style="width: 100%; height: 100%;"></div>
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
import Highcharts from 'highcharts'

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
const chartContainer = ref<HTMLElement | null>(null)
const selectedTimeRange = ref(12)
const loading = ref(false)
const error = ref('')
const modalTitle = ref('')

let chart: Highcharts.Chart | null = null
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
      
      const timestamps: number[] = []
      const values: number[] = []
      
      for (const point of dataPoints) {
        const date = new Date(point.timestamp)
        timestamps.push(date.getTime())
        values.push(point.value)
      }
      
      // Store data for chart rendering after loading completes
      loading.value = false
      
      // Wait for DOM to update (loading spinner removed, chart container shown)
      await nextTick()
      
      // Update chart
      if (chartContainer.value) {
        updateChart(timestamps, values, currentConfig)
      }
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load sensor data'
    console.error('Error fetching sensor history:', e)
    loading.value = false
  }
}

function updateChart(timestamps: number[], values: number[], config: SensorConfig) {
  if (!chartContainer.value) return
  
  // Destroy existing chart
  if (chart) {
    chart.destroy()
  }
  
  // Prepare data for Highcharts (array of [timestamp, value])
  const seriesData = timestamps.map((timestamp, index) => [timestamp, values[index]])
  
  // Create new Highcharts chart
  chart = (Highcharts as any).chart(chartContainer.value as HTMLElement, {
    chart: {
      type: 'line',
      backgroundColor: 'transparent',
      style: {
        fontFamily: 'inherit'
      }
    },
    title: {
      text: undefined
    },
    xAxis: {
      type: 'datetime',
      title: {
        text: t('time') || 'Time',
        style: {
          fontSize: '14px'
        }
      },
      dateTimeLabelFormats: {
        millisecond: '%H:%M:%S',
        second: '%H:%M:%S',
        minute: '%H:%M',
        hour: '%H:%M',
        day: '%m/%d<br/>%H:%M',
        week: '%m/%d',
        month: '%m/%Y',
        year: '%Y'
      },
      labels: {
        style: {
          fontSize: '12px'
        }
      }
    },
    yAxis: {
      title: {
        text: `${config.label} (${config.unit})`,
        style: {
          fontSize: '14px'
        }
      },
      labels: {
        formatter: function(this: Highcharts.AxisLabelsFormatterContextObject) {
          return (this.value as number).toFixed(1) + config.unit
        },
        style: {
          fontSize: '12px'
        }
      }
    },
    legend: {
      enabled: false
    },
    tooltip: {
      shared: true,
      crosshairs: true,
      xDateFormat: '%Y-%m-%d %H:%M',
      valueSuffix: config.unit,
      valueDecimals: 1,
      style: {
        fontSize: '13px'
      }
    },
    plotOptions: {
      line: {
        marker: {
          enabled: false,
          states: {
            hover: {
              enabled: true,
              radius: 5
            }
          }
        },
        lineWidth: 2
      },
      series: {
        fillOpacity: 0.1
      }
    },
    series: [{
      type: 'areaspline',
      name: config.label,
      data: seriesData,
      color: config.color,
      fillColor: config.backgroundColor
    }],
    credits: {
      enabled: false
    }
  })
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
