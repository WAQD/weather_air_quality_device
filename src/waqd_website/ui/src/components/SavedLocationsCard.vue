<template>
  <div id="saved_locations" class="order-4 xl:order-none card bg-base-100 shadow-xl">
    <div class="card-body p-3 sm:p-6">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="card-title text-base sm:text-lg">{{ t('home_weather_saved_location')
          }}</h2>
          <p class="mt-1 text-sm opacity-70">{{ t('home_weather_search_help') }}</p>
        </div>
      </div>

      <div v-if="successMessage" class="alert alert-success mt-4 py-3 text-sm">
        <span>{{ successMessage }}</span>
      </div>
      <div v-if="errorMessage" class="alert alert-error mt-4 py-3 text-sm">
        <span>{{ errorMessage }}</span>
      </div>

      <div v-if="currentLocation" class="mt-4 flex flex-col gap-2">
        <button v-if="!isCurrentLocationSaved" class="btn btn-primary" type="button"
          :disabled="isSavingLocation" @click="saveCurrentLocation">
          {{ t('save') }}
        </button>
        <button v-else class="btn btn-outline" type="button" :disabled="isSavingLocation"
          @click="setAsHome(currentLocation)">
          {{ t('set_home') }}
        </button>
      </div>

      <div v-if="savedLocations.length > 0" class="mt-5 space-y-2">
        <p class="text-xs font-semibold uppercase tracking-[0.16em] opacity-60">
          {{ t('saved_locations') }}</p>
        <div v-for="location in savedLocations" :key="getLocationKey(location)"
          class="rounded-box border border-base-300 bg-base-200/70 p-3">
          <div class="min-w-0">
            <p class="font-semibold truncate break-words">{{ location.name }}</p>
          </div>

          <div class="mt-2 flex flex-col gap-2">
            <div class="text-xs opacity-70">{{ location.state || location.country }}
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="btn btn-xs" type="button" @click="selectLocation(location)">{{
                t('open') }}</button>
              <button class="btn btn-xs btn-outline" type="button" :disabled="isSavingLocation"
                @click="setAsHome(location)">{{
                  t('set_home') }}</button>
              <button class="btn btn-xs btn-ghost" type="button" :disabled="isSavingLocation"
                @click="removeSavedLocation(location)">{{ t('delete') }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTranslation } from '../composables/useTranslation'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'

const { t } = useTranslation()
const {
  currentLocation,
  savedLocations,
  errorMessage,
  successMessage,
  isSavingLocation,
  clearSuccess,
  clearError,
  saveLocation,
  setHomeLocation,
  setCurrentLocation,
  loadWeatherForLocation,
  removeSavedLocation: removeSavedLocationEntry,
  getLocationKey
} = useWebsiteWeather()

const isCurrentLocationSaved = computed(() => {
  if (!currentLocation.value) {
    return false
  }

  return savedLocations.value.some((loc) => getLocationKey(loc) === getLocationKey(currentLocation.value as WeatherLocationPayload))
})

async function saveCurrentLocation(): Promise<void> {
  if (!currentLocation.value) {
    return
  }

  clearSuccess()
  clearError()
  const saved = await saveLocation(currentLocation.value, false)
  if (!saved) {
    return
  }

  successMessage.value = t('home_weather_saved')
}

async function setAsHome(location: WeatherLocationPayload): Promise<void> {
  clearSuccess()
  clearError()
  const saved = await setHomeLocation(location)
  if (!saved) {
    return
  }

  successMessage.value = t('saved_as_home')
}

async function selectLocation(location: WeatherLocationPayload): Promise<void> {
  clearSuccess()
  clearError()
  setCurrentLocation(location)
  await loadWeatherForLocation(location)
}

async function removeSavedLocation(location: WeatherLocationPayload): Promise<void> {
  clearSuccess()
  clearError()

  const deleted = await removeSavedLocationEntry(location)
  if (!deleted) {
    return
  }

  successMessage.value = t('home_weather_removed')
}
</script>
