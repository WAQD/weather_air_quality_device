<template>
  <div id="saved_locations" class="card bg-base-100 shadow-xl">
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

      <div v-if="locationEntries.length > 0" class="mt-5 space-y-2">
        <p class="text-xs font-semibold uppercase tracking-[0.16em] opacity-60">
          {{ t('saved_locations') }}</p>
        <div v-for="entry in locationEntries" :key="entryKey(entry)" class="rounded-box border p-3"
          :class="entry.isDevice
            ? 'border-primary/40 bg-primary/10'
            : 'border-base-300 bg-base-200/70'">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="font-semibold truncate wrap-break-word">{{ entry.displayName }}</p>
            </div>
            <div class="flex flex-none flex-wrap justify-end gap-1">
              <span v-if="entry.isDevice" class="badge badge-primary badge-sm">
                {{ t('current_location') }}
              </span>
              <span v-if="isHome(entry.location)" class="badge badge-ghost badge-sm">
                {{ t('home') }}
              </span>
            </div>
          </div>

          <div class="mt-2 flex flex-col gap-2">
            <div class="text-xs opacity-70">{{ entry.location.state || entry.location.country }}
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="btn btn-xs" type="button" @click="selectLocation(entry.location)">{{
                t('open') }}</button>
              <button class="btn btn-xs btn-outline" type="button"
                :disabled="isSavingLocation || isHome(entry.location)"
                @click="setAsHome(entry.location)">{{
                  t('set_home') }}</button>
              <button v-if="!entry.isDevice" class="btn btn-xs btn-ghost" type="button"
                :disabled="isSavingLocation" @click="removeSavedLocation(entry.location)">{{
                  t('delete') }}</button>
            </div>
          </div>
        </div>
      </div>
      <p v-else-if="isResolvingDeviceLocation" class="mt-5 text-sm opacity-70">
        {{ t('current_location') }}…
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'

interface LocationEntry {
  location: WeatherLocationPayload
  isDevice: boolean
  displayName: string
}

const router = useRouter()
const { t } = useTranslation()
const {
  savedLocations,
  homeLocation,
  deviceLocation,
  errorMessage,
  successMessage,
  isSavingLocation,
  isResolvingDeviceLocation,
  clearSuccess,
  clearError,
  setHomeLocation,
  setCurrentLocation,
  loadWeather,
  loadWeatherForLocation,
  resolveDeviceLocation,
  removeSavedLocation: removeSavedLocationEntry,
  getLocationKey
} = useWebsiteWeather()

// The current GPS position is presented as a pseudo saved location. It cannot
// be deleted, but it can be opened and set as the home location.
const deviceKey = computed(() => deviceLocation.value ? getLocationKey(deviceLocation.value) : null)

const locationEntries = computed<LocationEntry[]>(() => {
  const entries: LocationEntry[] = []

  if (deviceLocation.value) {
    entries.push({
      location: deviceLocation.value,
      isDevice: true,
      displayName: deviceLocation.value.name || t('current_location')
    })
  }

  for (const location of savedLocations.value) {
    // Avoid duplicating the current position if it was also saved explicitly.
    if (deviceKey.value && getLocationKey(location) === deviceKey.value) {
      continue
    }
    entries.push({
      location,
      isDevice: false,
      displayName: location.name || t('current_location')
    })
  }

  return entries
})

function entryKey(entry: LocationEntry): string {
  return entry.isDevice ? 'device' : getLocationKey(entry.location)
}

function isHome(location: WeatherLocationPayload): boolean {
  return Boolean(homeLocation.value) &&
    getLocationKey(homeLocation.value as WeatherLocationPayload) === getLocationKey(location)
}

onMounted(() => {
  void resolveDeviceLocation()
})

async function setAsHome(location: WeatherLocationPayload): Promise<void> {
  clearSuccess()
  clearError()
  const saved = await setHomeLocation(location)
  if (!saved) {
    return
  }

  // Refresh the weather shown on the home card for the new home location.
  await loadWeather(false)
  successMessage.value = t('saved_as_home')
}

async function selectLocation(location: WeatherLocationPayload): Promise<void> {
  clearSuccess()
  clearError()
  setCurrentLocation(location)
  await router.push({ name: 'weather' })
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
