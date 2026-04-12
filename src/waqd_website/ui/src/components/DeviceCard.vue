<template>
  <div
    class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all overflow-hidden min-h-[280px]"
    :style="getWeatherBackground(props.device.device_id)">
    <div class="card-body bg-base-100/80 backdrop-blur-sm flex flex-col">
      <div class="flex justify-between items-start mb-2">
        <h2 class="card-title text-xl">{{ props.device.name }}</h2>
        <div class="badge" :class="props.device.status === 'online' ? 'badge-success' : 'badge-error'">
          {{ props.device.status }}
        </div>
      </div>

      <div class="space-y-2 text-sm opacity-70 flex-grow">
        <div class="flex items-center gap-2">
          <svg class="h-6 w-6"><use :href="locationIconUrl" fill="currentColor" /></svg>
          <span>{{ props.device.location || t('no_location') }}</span>
        </div>
        <div class="flex items-center gap-2">
          <svg class="h-6 w-6"><use :href="codeXmlIconUrl" fill="currentColor" /></svg>
          <span class="font-mono text-xs">{{ props.device.device_id }}</span>
        </div>
        <div v-if="props.device.last_seen" class="flex items-center gap-2">
          <svg class="h-6 w-6"><use :href="lastSeenIconUrl" fill="currentColor" /></svg>
          <span>{{ t('last_seen') }}: {{ formatDate(props.device.last_seen) }}</span>
        </div>
      </div>

      <div class="card-actions flex-col items-stretch mt-auto pt-4 gap-2">
        <div v-if="props.showManagementActions" class="flex gap-2 justify-end">
          <button class="btn btn-sm btn-ghost" @click="$emit('edit', props.device)">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20"
              fill="currentColor">
              <path
                d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>
          <button class="btn btn-sm btn-ghost" @click="$emit('share', props.device)">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20"
              fill="currentColor">
              <path
                d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
            </svg>
          </button>
          <button class="btn btn-sm btn-error" @click="$emit('delete', props.device)">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20"
              fill="currentColor">
              <path fill-rule="evenodd"
                d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                clip-rule="evenodd" />
            </svg>
          </button>
        </div>
        <button v-if="props.showConnectButton" class="btn btn-sm btn-primary w-full"
          @click="$emit('connect', props.device)" :disabled="props.device.status !== 'online'">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20"
            fill="currentColor">
            <path
              d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
            <path
              d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
          </svg>
          {{ t('connect') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useTranslation } from '../composables/useTranslation'
import { useWeather } from '../composables/useWeather'
import type { Device } from '../types/device'

const props = withDefaults(defineProps<{
  device: Device
  showManagementActions?: boolean
  showConnectButton?: boolean
}>(), {
  showManagementActions: true,
  showConnectButton: true,
})

defineEmits<{
  edit: [device: Device]
  share: [device: Device]
  delete: [device: Device]
  connect: [device: Device]
}>()

const { t } = useTranslation()
const { getWeatherBackground } = useWeather()
const lastSeenIconUrl = '/static/weather_icons/wi-time-8.svg#Layer_1'
const codeXmlIconUrl = '/static/general_icons/code_xml.svg#main'
const locationIconUrl = '/static/general_icons/location.svg#main'

function formatDate(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return t('just_now')
  if (diffMins < 60) return `${diffMins} ${t('minutes_ago')}`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours} ${t('hours_ago')}`

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays} ${t('days_ago')}`

  return date.toLocaleDateString()
}
</script>