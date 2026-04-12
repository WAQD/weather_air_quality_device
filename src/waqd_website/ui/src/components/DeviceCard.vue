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
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20"
            fill="currentColor">
            <path fill-rule="evenodd"
              d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
              clip-rule="evenodd" />
          </svg>
          <span>{{ props.device.location || t('no_location') }}</span>
        </div>
        <div class="flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20"
            fill="currentColor">
            <path fill-rule="evenodd"
              d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z"
              clip-rule="evenodd" />
          </svg>
          <span class="font-mono text-xs">{{ props.device.device_id }}</span>
        </div>
        <div v-if="props.device.last_seen" class="flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20"
            fill="currentColor">
            <path fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
              clip-rule="evenodd" />
          </svg>
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