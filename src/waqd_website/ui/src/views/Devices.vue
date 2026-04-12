<template>
  <div class="container mx-auto px-4 sm:px-8 py-8">
    <h1 class="text-4xl font-bold mb-8">{{ t('my_devices') }}</h1>

    <!-- Toast Container -->
    <div class="toast toast-bottom toast-end z-50">
      <div v-if="showSuccessToast" class="alert alert-success">
        <span>{{ toastMessage }}</span>
        <button class="btn btn-square btn-success" @click="showSuccessToast = false">
          <svg viewBox="0 0 24 24" class="h-4">
            <use :href="cancelIconUrl" fill="white" />
          </svg>
        </button>
      </div>
      <div v-if="showErrorToast" class="alert alert-error">
        <span>{{ toastMessage }}</span>
        <button class="btn btn-square btn-error" @click="showErrorToast = false">
          <svg viewBox="0 0 24 24" class="h-4">
            <use :href="cancelIconUrl" fill="white" />
          </svg>
        </button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center items-center min-h-[50vh]">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else class="space-y-6">
      <!-- Add New Device Button -->
      <div class="flex justify-end mb-4">
        <button class="btn btn-primary" @click="openAddDeviceModal">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20"
            fill="currentColor">
            <path fill-rule="evenodd"
              d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
              clip-rule="evenodd" />
          </svg>
          {{ t('pair_device') }}
        </button>
      </div>

      <!-- Empty State -->
      <div v-if="devices.length === 0" class="card bg-base-200 shadow-xl">
        <div class="card-body items-center text-center py-16">
          <svg xmlns="http://www.w3.org/2000/svg"
            class="h-24 w-24 text-base-content opacity-30 mb-4" fill="none" viewBox="0 0 24 24"
            stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <h2 class="text-2xl font-semibold mb-2">{{ t('no_devices_yet') }}</h2>
          <p class="text-base-content opacity-70 mb-4">{{ t('add_your_first_device') }}</p>
          <button class="btn btn-primary" @click="openAddDeviceModal">
            {{ t('pair_device') }}
          </button>
        </div>
      </div>

      <!-- Devices Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <DeviceCard v-for="device in devices" :key="device.id" :device="device"
          @edit="openEditModal" @share="openShareModal" @delete="openDeleteModal"
          @connect="connectToDevice" />
      </div>
    </div>

    <!-- Pairing Modal -->
    <dialog ref="pairingModal" class="modal">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-2xl mb-4">{{ t('pair_device') }}</h3>

        <!-- Instructions -->
        <div class="alert alert-info mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24"
            stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p class="font-semibold">{{ t('pairing_instructions_title') }}</p>
            <ol class="list-decimal list-inside text-sm mt-2">
              <li>{{ t('pairing_step_1') }}</li>
              <li>{{ t('pairing_step_2') }}</li>
              <li>{{ t('pairing_step_3') }}</li>
            </ol>
          </div>
        </div>

        <!-- Pairing State: Entering Passphrase -->
        <div v-if="pairingState === 'input'" class="space-y-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text text-lg">{{ t('enter_passphrase') }}</span>
            </label>
            <input v-model="passphrase" type="text"
              class="input input-bordered input-lg text-center font-mono text-2xl uppercase tracking-widest"
              maxlength="6" @input="passphrase = passphrase.toUpperCase()" />
            <label class="label">
              <span class="label-text-alt">{{ t('passphrase_case_insensitive') }}</span>
            </label>
          </div>

          <!-- QR Code Display Area (Optional) -->
          <div v-if="qrCodeData"
            class="flex flex-col items-center gap-2 bg-base-200 p-4 rounded-box">
            <p class="text-sm opacity-70">{{ t('or_scan_qr_code') }}</p>
            <img :src="qrCodeData" alt="QR Code" class="w-48 h-48" />
          </div>

          <div class="modal-action">
            <button class="btn" @click="closePairingModal">{{ t('cancel') }}</button>
            <button class="btn btn-primary" @click="claimDevice"
              :disabled="passphrase.length !== 6 || claiming">
              <span v-if="claiming" class="loading loading-spinner loading-sm mr-2"></span>
              {{ t('claim_device') }}
            </button>
          </div>
        </div>

        <!-- Pairing State: Waiting for Device Confirmation -->
        <div v-else-if="pairingState === 'waiting'" class="space-y-4">
          <div class="flex flex-col items-center gap-4 py-8">
            <span class="loading loading-spinner loading-lg"></span>
            <p class="text-lg font-semibold">{{ t('waiting_for_device_confirmation') }}</p>
            <p class="text-sm opacity-70 text-center">{{ t('check_device_screen') }}</p>
          </div>
          <div class="modal-action">
            <button class="btn" @click="cancelPairing">{{ t('cancel') }}</button>
          </div>
        </div>

        <!-- Pairing State: Success -->
        <div v-else-if="pairingState === 'success'" class="space-y-4">
          <div class="flex flex-col items-center gap-4 py-8">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24 text-success" fill="none"
              viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-2xl font-bold text-success">{{ t('pairing_successful') }}</p>
            <p class="text-sm opacity-70">{{ t('device_added_to_list') }}</p>
          </div>
          <div class="modal-action">
            <button class="btn btn-primary" @click="closePairingModal">{{ t('close') }}</button>
          </div>
        </div>

        <!-- Pairing State: Error -->
        <div v-else-if="pairingState === 'error'" class="space-y-4">
          <div class="flex flex-col items-center gap-4 py-8">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24 text-error" fill="none"
              viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-2xl font-bold text-error">{{ t('pairing_failed') }}</p>
            <p class="text-sm opacity-70">{{ pairingError }}</p>
          </div>
          <div class="modal-action">
            <button class="btn" @click="resetPairingModal">{{ t('try_again') }}</button>
            <button class="btn btn-ghost" @click="closePairingModal">{{ t('cancel') }}</button>
          </div>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closePairingModal">close</button>
      </form>
    </dialog>

    <!-- Edit Device Modal -->
    <dialog ref="editModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">{{ t('edit_device') }}</h3>
        <div class="space-y-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">{{ t('device_name') }}</span>
            </label>
            <input v-model="editDeviceName" type="text" class="input input-bordered"
              :placeholder="deviceToEdit?.name || t('device_name')" />
          </div>
          <div class="form-control">
            <label class="label">
              <span class="label-text">{{ t('location') }}</span>
            </label>
            <input v-model="editDeviceLocation" type="text" class="input input-bordered"
              :placeholder="deviceToEdit?.location || t('location')" />
          </div>
        </div>
        <div class="modal-action">
          <button class="btn" @click="closeEditModal">{{ t('cancel') }}</button>
          <button class="btn btn-primary" @click="saveDeviceEdit" :disabled="savingEdit">
            <span v-if="savingEdit" class="loading loading-spinner loading-sm mr-2"></span>
            {{ t('save') }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeEditModal">close</button>
      </form>
    </dialog>

    <!-- Share Device Modal -->
    <dialog ref="shareModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">{{ t('share_device') }}</h3>
        <p class="text-sm opacity-70 mb-4">{{ t('share_device_description') }}</p>
        <div class="form-control">
          <label class="label">
            <span class="label-text">{{ t('username') }}</span>
          </label>
          <input v-model="shareUsername" type="text" class="input input-bordered"
            :placeholder="t('enter_username')" />
        </div>
        <div class="modal-action">
          <button class="btn" @click="closeShareModal">{{ t('cancel') }}</button>
          <button class="btn btn-primary" @click="shareDeviceWithUser"
            :disabled="!shareUsername || sharingDevice">
            <span v-if="sharingDevice" class="loading loading-spinner loading-sm mr-2"></span>
            {{ t('share') }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeShareModal">close</button>
      </form>
    </dialog>

    <!-- Delete Device Modal -->
    <dialog ref="deleteModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">{{ t('delete_device') }}</h3>
        <p class="py-4">
          {{ t('delete_device_confirmation') }} <strong>{{ deviceToDelete?.name }}</strong>?
        </p>
        <div class="modal-action">
          <button class="btn" @click="closeDeleteModal">{{ t('cancel') }}</button>
          <button class="btn btn-error" @click="deleteDevice">
            <span v-if="deletingDevice" class="loading loading-spinner loading-sm mr-2"></span>
            {{ t('delete') }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeDeleteModal">close</button>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'
import { useWeather } from '../composables/useWeather'
import QRCode from 'qrcode'
import DeviceCard from '../components/DeviceCard.vue'
import type { Device } from '../types/device'

const router = useRouter()
const { t } = useTranslation()
const { setWeatherData } = useWeather()

const cancelIconUrl = '/static/general_icons/cancel.svg#main'

const loading = ref(true)
const devices = ref<Device[]>([])
const pairingModal = ref<HTMLDialogElement | null>(null)
const deleteModal = ref<HTMLDialogElement | null>(null)
const editModal = ref<HTMLDialogElement | null>(null)
const shareModal = ref<HTMLDialogElement | null>(null)
const deviceToDelete = ref<Device | null>(null)
const deviceToEdit = ref<Device | null>(null)
const deviceToShare = ref<Device | null>(null)
const deletingDevice = ref(false)
const savingEdit = ref(false)
const sharingDevice = ref(false)
const editDeviceName = ref('')
const editDeviceLocation = ref('')
const shareUsername = ref('')
const showSuccessToast = ref(false)
const showErrorToast = ref(false)
const toastMessage = ref('')

// Pairing state
const pairingState = ref<'input' | 'waiting' | 'success' | 'error'>('input')
const passphrase = ref('')
const qrCodeData = ref('')
const claiming = ref(false)
const pairingError = ref('')
let currentSessionId: string | null = null
let pollingInterval: number | null = null
let deviceStatusPollingInterval: number | null = null

onMounted(async () => {
  await loadDevices()
  startDeviceStatusPolling()
})

async function loadDevices() {
  loading.value = true
  try {
    const response = await fetch('/api/user/devices', {
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error('Failed to load devices')
    }

    const data = await response.json()
    devices.value = data.devices || []

    // Store weather data for each device in the composable
    devices.value.forEach(device => {
      if (device.weather) {
        setWeatherData(device.device_id, device.weather)
      }
    })
  } catch (error) {
    console.error('Error loading devices:', error)
    showToast('error', t('error_loading_devices'))
  } finally {
    loading.value = false
  }
}

async function updateDeviceStatus() {
  try {
    const response = await fetch('/api/user/devices', {
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error('Failed to update device status')
    }

    const data = await response.json()
    const updatedDevices = data.devices || []

    // Update existing devices without triggering full re-render
    updatedDevices.forEach((updatedDevice: Device) => {
      const existingDevice = devices.value.find(d => d.id === updatedDevice.id)
      if (existingDevice) {
        existingDevice.status = updatedDevice.status
        existingDevice.last_seen = updatedDevice.last_seen
        // Update weather data if available
        if (updatedDevice.weather) {
          existingDevice.weather = updatedDevice.weather
          setWeatherData(updatedDevice.device_id, updatedDevice.weather)
        }
      }
    })
  } catch (error) {
    console.error('Error updating device status:', error)
  }
}

function startDeviceStatusPolling() {
  // Poll every 5 seconds
  deviceStatusPollingInterval = window.setInterval(async () => {
    await updateDeviceStatus()
  }, 10000)
}

function stopDeviceStatusPolling() {
  if (deviceStatusPollingInterval !== null) {
    clearInterval(deviceStatusPollingInterval)
    deviceStatusPollingInterval = null
  }
}

// Pairing Modal Functions
function openAddDeviceModal() {
  openPairingModal()
}

function openPairingModal() {
  resetPairingModal()
  pairingModal.value?.showModal()
}

function closePairingModal() {
  pairingModal.value?.close()
  stopPolling()
  resetPairingModal()
}

function resetPairingModal() {
  pairingState.value = 'input'
  passphrase.value = ''
  qrCodeData.value = ''
  claiming.value = false
  pairingError.value = ''
  currentSessionId = null
}

async function claimDevice() {
  if (passphrase.value.length !== 6) return

  claiming.value = true

  try {
    const response = await fetch('/api/user/devices/claim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ passphrase: passphrase.value }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      console.error('API Error Response:', errorData)
      throw new Error(errorData.detail || errorData.message)
    }

    const data = await response.json()
    console.log('Claim response:', data)

    if (!data.success) {
      throw new Error(data.message)
    }

    currentSessionId = data.session_id
    pairingState.value = 'waiting'

    // Start polling for device confirmation
    startPolling()
  } catch (error) {
    console.error('Error claiming device:', error)
    pairingState.value = 'error'
    pairingError.value = error instanceof Error ? error.message : 'Failed to claim device'
    claiming.value = false
  } finally {
    claiming.value = false
  }
}

function startPolling() {
  let pollAttempts = 0
  const maxAttempts = 60 // Poll for up to 60 seconds

  pollingInterval = window.setInterval(async () => {
    pollAttempts++

    if (!currentSessionId) {
      stopPolling()
      return
    }

    try {
      const response = await fetch(`/api/user/devices/session/${currentSessionId}/status`, {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to check pairing status')
      }

      const data = await response.json()

      // Check if pairing is complete
      if (data.status === 'approved') {
        stopPolling()
        pairingState.value = 'success'

        // Reload devices list
        await loadDevices()

        // Auto-close after showing success
        setTimeout(() => {
          closePairingModal()
          showToast('success', t('device_paired_successfully'))
        }, 2000)
      } else if (data.status === 'rejected' || data.status === 'expired') {
        stopPolling()
        pairingState.value = 'error'
        pairingError.value = data.status === 'rejected'
          ? 'Device pairing was rejected'
          : 'Pairing session expired'
      }

      // Timeout if polling too long
      if (pollAttempts >= maxAttempts) {
        stopPolling()
        pairingState.value = 'error'
        pairingError.value = 'Pairing timeout - please try again'
      }
    } catch (error) {
      console.error('Error checking pairing status:', error)
      // Continue polling unless we hit max attempts
      if (pollAttempts >= maxAttempts) {
        stopPolling()
        pairingState.value = 'error'
        pairingError.value = 'Connection error - please try again'
      }
    }
  }, 2000) // Poll every 2 seconds
}

function stopPolling() {
  if (pollingInterval !== null) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

function cancelPairing() {
  stopPolling()
  closePairingModal()
}

function openDeleteModal(device: Device) {
  deviceToDelete.value = device
  deleteModal.value?.showModal()
}

function closeDeleteModal() {
  deleteModal.value?.close()
  deviceToDelete.value = null
}

async function deleteDevice() {
  if (!deviceToDelete.value) return

  deletingDevice.value = true
  try {
    const response = await fetch(`/api/user/devices/${deviceToDelete.value.device_id}`, {
      method: 'DELETE',
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error('Failed to delete device')
    }

    devices.value = devices.value.filter(d => d.id !== deviceToDelete.value?.id)
    showToast('success', t('device_deleted_successfully'))
    closeDeleteModal()
  } catch (error) {
    console.error('Error deleting device:', error)
    showToast('error', t('error_deleting_device'))
  } finally {
    deletingDevice.value = false
  }
}

function openEditModal(device: Device) {
  deviceToEdit.value = device
  editDeviceName.value = device.name || ''
  editDeviceLocation.value = device.location || ''
  editModal.value?.showModal()
}

function closeEditModal() {
  editModal.value?.close()
  deviceToEdit.value = null
  editDeviceName.value = ''
  editDeviceLocation.value = ''
}

async function saveDeviceEdit() {
  if (!deviceToEdit.value) return

  savingEdit.value = true
  try {
    const response = await fetch(`/api/user/devices/${deviceToEdit.value.device_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        name: editDeviceName.value || null,
        location: editDeviceLocation.value || null,
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to update device')
    }

    const data = await response.json()

    // Update the device in the list
    const deviceIndex = devices.value.findIndex(d => d.id === deviceToEdit.value?.id)
    if (deviceIndex !== -1 && data.device) {
      const updatedDevice = devices.value[deviceIndex]
      if (updatedDevice) {
        updatedDevice.name = data.device.name
        updatedDevice.location = data.device.location
      }
    }

    showToast('success', t('device_updated_successfully'))
    closeEditModal()
  } catch (error) {
    console.error('Error updating device:', error)
    showToast('error', t('error_updating_device'))
  } finally {
    savingEdit.value = false
  }
}

function openShareModal(device: Device) {
  deviceToShare.value = device
  shareUsername.value = ''
  shareModal.value?.showModal()
}

function closeShareModal() {
  shareModal.value?.close()
  deviceToShare.value = null
  shareUsername.value = ''
}

async function shareDeviceWithUser() {
  if (!deviceToShare.value || !shareUsername.value) return

  sharingDevice.value = true
  try {
    const response = await fetch(`/api/user/devices/${deviceToShare.value.device_id}/share`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        username: shareUsername.value,
      }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to share device')
    }

    showToast('success', t('device_shared_successfully') || `Device shared successfully with ${shareUsername.value}`)
    closeShareModal()
  } catch (error) {
    console.error('Error sharing device:', error)
    showToast('error', error instanceof Error ? error.message : t('error_sharing_device'))
  } finally {
    sharingDevice.value = false
  }
}

function connectToDevice(device: Device) {
  // Navigate to device detail page
  router.push(`/rest/device/${device.id}`)
}

function showToast(type: 'success' | 'error', message: string) {
  toastMessage.value = message
  if (type === 'success') {
    showSuccessToast.value = true
    setTimeout(() => showSuccessToast.value = false, 5000)
  } else {
    showErrorToast.value = true
    setTimeout(() => showErrorToast.value = false, 5000)
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopPolling()
  stopDeviceStatusPolling()
})
</script>

<style scoped>
/* Add any component-specific styles here */
</style>


