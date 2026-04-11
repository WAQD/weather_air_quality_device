import { ref, computed } from 'vue'

export interface WeatherData {
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
  humidity: number
  clouds: number
  precipitation_probability?: number
  precipitation?: number
}

export interface ForecastData {
  main: string
  temp: number
  temp_min: number
  temp_max: number
  temp_night_min: number
  temp_night_max: number
  icon: string
  date_time: string
  wid: number
  wind_speed: number
  wind_deg: number
  sunrise: string
  sunset: string
  pressure: number
  humidity: number
  clouds: number
  precipitation_probability_max?: number
  precipitation?: number
}

export interface HourlyWeatherData {
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
  precipitation_probability?: number
  precipitation?: number
}

// Global weather data store (shared across all components)
const weatherStore = ref<Map<string, WeatherData>>(new Map())
const forecastStore = ref<Map<string, ForecastData[]>>(new Map())
const hourlyDaytimeStore = ref<Map<string, HourlyWeatherData[][]>>(new Map())
const hourlyNighttimeStore = ref<Map<string, HourlyWeatherData[][]>>(new Map())

export function useWeather() {
  const setWeatherData = (deviceId: string, weather: WeatherData) => {
    weatherStore.value.set(deviceId, weather)
  }

  const getWeatherData = (deviceId: string): WeatherData | undefined => {
    return weatherStore.value.get(deviceId)
  }

  const clearWeatherData = (deviceId: string) => {
    weatherStore.value.delete(deviceId)
  }

  const hasWeatherData = (deviceId: string): boolean => {
    return weatherStore.value.has(deviceId)
  }

  const setForecastData = (deviceId: string, forecast: ForecastData[]) => {
    forecastStore.value.set(deviceId, forecast)
  }

  const getForecastData = (deviceId: string): ForecastData[] | undefined => {
    return forecastStore.value.get(deviceId)
  }

  const clearForecastData = (deviceId: string) => {
    forecastStore.value.delete(deviceId)
  }

  const hasForecastData = (deviceId: string): boolean => {
    return forecastStore.value.has(deviceId)
  }

  const setHourlyForecastData = (deviceId: string, daytime: HourlyWeatherData[][], nighttime: HourlyWeatherData[][]) => {
    hourlyDaytimeStore.value.set(deviceId, daytime)
    hourlyNighttimeStore.value.set(deviceId, nighttime)
  }

  const getHourlyDaytimeData = (deviceId: string): HourlyWeatherData[][] | undefined => {
    return hourlyDaytimeStore.value.get(deviceId)
  }

  const getHourlyNighttimeData = (deviceId: string): HourlyWeatherData[][] | undefined => {
    return hourlyNighttimeStore.value.get(deviceId)
  }

  const clearHourlyForecastData = (deviceId: string) => {
    hourlyDaytimeStore.value.delete(deviceId)
    hourlyNighttimeStore.value.delete(deviceId)
  }

  const hasHourlyForecastData = (deviceId: string): boolean => {
    return hourlyDaytimeStore.value.has(deviceId) || hourlyNighttimeStore.value.has(deviceId)
  }

  const getWeatherBackground = (deviceId: string): { backgroundImage?: string; backgroundSize?: string; backgroundPosition?: string; backgroundRepeat?: string } => {
    const weather = getWeatherData(deviceId)
    if (!weather) return {}

    const main = weather.main.toLowerCase()
    const isDaytime = isDay(weather)
    const timePrefix = isDaytime ? 'day' : 'night'

    // Map weather conditions to available backgrounds
    // Night backgrounds are limited, so we map missing ones to available alternatives
    const weatherMapping: { [key: string]: { day: string; night: string } } = {
      'clear': { day: 'clear', night: 'clear' },
      'clouds': { day: 'clouds', night: 'heavy_clouds' },
      'heavy_clouds': { day: 'heavy_clouds', night: 'heavy_clouds' },
      'fog': { day: 'fog', night: 'heavy_clouds' },
      'mist': { day: 'mist', night: 'heavy_clouds' },
      'drizzle': { day: 'drizzle', night: 'rain' },
      'rain': { day: 'rain', night: 'rain' },
      'snow': { day: 'snow', night: 'snow' },
      'thunderstorm': { day: 'thunderstorm', night: 'rain' },
      'squall': { day: 'squall', night: 'rain' }
    }

    // Get the mapped background name
    const mapping = weatherMapping[main]
    const bgName = mapping ? mapping[isDaytime ? 'day' : 'night'] : 'clouds'
    
    // Construct background image URL
    const bgUrl = `/static/weather_bgrs/bg_${timePrefix}_${bgName}.jpg`

    return {
      backgroundImage: `url(${bgUrl})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    }
  }

  const isDay = (weather: WeatherData): boolean => {
    const now = new Date()
    
    // Parse time strings in format "HH:MM:SS" to today's date
    const parseTimeString = (timeStr: string): Date => {
      const parts = timeStr.split(':').map(Number)
      const hours = parts[0] || 0
      const minutes = parts[1] || 0
      const seconds = parts[2] || 0
      const date = new Date()
      date.setHours(hours, minutes, seconds, 0)
      return date
    }
    
    const sunrise = parseTimeString(weather.sunrise)
    const sunset = parseTimeString(weather.sunset)

    return now >= sunrise && now <= sunset
  }

  return {
    setWeatherData,
    getWeatherData,
    clearWeatherData,
    hasWeatherData,
    setForecastData,
    getForecastData,
    clearForecastData,
    hasForecastData,
    setHourlyForecastData,
    getHourlyDaytimeData,
    getHourlyNighttimeData,
    clearHourlyForecastData,
    hasHourlyForecastData,
    getWeatherBackground,
    isDay
  }
}
