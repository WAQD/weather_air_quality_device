import { ref } from 'vue'

export interface SensorDataPoint {
  timestamp: string
  value: number
}

export interface SensorHistoryData {
  'temp_degC'?: SensorDataPoint[]
  'humidity_%'?: SensorDataPoint[]
  'CO2_ppm'?: SensorDataPoint[]
  'pressure_hPa'?: SensorDataPoint[]
}

// Global sensor history store (shared across all components)
const sensorHistoryStore = ref<Map<string, SensorHistoryData>>(new Map())

export function useSensorHistory() {
  const setSensorHistory = (deviceId: string, history: SensorHistoryData) => {
    sensorHistoryStore.value.set(deviceId, history)
  }

  const getSensorHistory = (deviceId: string): SensorHistoryData | undefined => {
    return sensorHistoryStore.value.get(deviceId)
  }

  const getSensorTypeHistory = (deviceId: string, sensorType: string): SensorDataPoint[] | undefined => {
    const history = sensorHistoryStore.value.get(deviceId)
    if (!history) return undefined
    return history[sensorType as keyof SensorHistoryData]
  }

  const clearSensorHistory = (deviceId: string) => {
    sensorHistoryStore.value.delete(deviceId)
  }

  const hasSensorHistory = (deviceId: string): boolean => {
    return sensorHistoryStore.value.has(deviceId)
  }

  return {
    setSensorHistory,
    getSensorHistory,
    getSensorTypeHistory,
    clearSensorHistory,
    hasSensorHistory
  }
}
