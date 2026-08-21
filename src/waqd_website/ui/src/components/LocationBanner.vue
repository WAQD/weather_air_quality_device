<template>
  <div v-if="currentLocation" id="current_location_banner"
    class="order-1 sticky top-2 z-20 rounded-box border border-base-300 bg-base-100/70 backdrop-blur-md p-2.5 sm:p-4 overflow-hidden"
    :style="weatherHeroStyle">
    <div class="flex items-start gap-3">
      <div class="text-2xl font-thin tabular-nums hidden sm:block min-w-10 text-center">
        {{ currentLocation.country_code }}
      </div>
      <div>
        <img class="size-8 rounded-box p-1 bg-base-100"
          :src="getFlagIconUrl(currentLocation.country_code)" :alt="currentLocation.country_code"
          :style="{ visibility: flagLoaded ? 'visible' : 'hidden' }" @load="flagLoaded = true"
          @error="flagLoaded = false" />
      </div>
      <div class="flex-1 min-w-0 flex items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="text-2xl font-thin whitespace-nowrap">
            {{ currentLocation.name }}</div>
        </div>
        <div class="shrink-0 text-right max-w-[11rem] sm:max-w-[16rem]">
          <div class="text-xs uppercase font-semibold opacity-60 truncate">
            {{ currentLocation.state || currentLocation.county ||
              currentLocation.country }}
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else id="no_location_banner"
    class="order-1 rounded-box border border-dashed border-base-300 bg-base-200/60 p-4 text-sm opacity-80">
    {{ t('home_weather_needs_location') }}
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import { useWeather } from '../composables/useWeather'
import { useWebsiteWeather } from '../composables/useWebsiteWeather'
import { getFlagIconUrl } from '../utils/weather'

const WEATHER_VIEW_KEY = 'website-weather-view'

const { t } = useTranslation()
const { getWeatherBackground } = useWeather()
const { currentLocation, currentWeather } = useWebsiteWeather()

const flagLoaded = ref(false)
watch(() => currentLocation.value?.country_code, () => {
  flagLoaded.value = false
})

const weatherHeroStyle = computed(() => {
  if (!currentWeather.value) {
    return {}
  }

  return getWeatherBackground(WEATHER_VIEW_KEY)
})
</script>
