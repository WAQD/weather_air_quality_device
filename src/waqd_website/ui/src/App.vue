<template>
  <Navbar />
  <div class="bg-gradient-to-b from-base-200 to-base-300 overflow-x-hidden">
    <router-view />
  </div>
  
  <!-- PWA Update Notification -->
  <div v-if="needRefresh" class="toast toast-top toast-center z-50"> 
    <div class="alert alert-info shadow-lg">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <div>
        <h3 class="font-bold">Update available</h3>
        <div class="text-xs">Current version: {{ appVersion }}</div>
      </div>
      <button class="btn btn-sm btn-primary" @click="updateApp">Apply</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import Navbar from './components/Navbar.vue'
import { useUser } from './composables/useUser'
import { useTokenRefresh } from './composables/useTokenRefresh'
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { fetchUserInfo } = useUser()
const { stopRefreshTimer } = useTokenRefresh()
const appVersion = __APP_VERSION__

// PWA update handling
const { needRefresh, updateServiceWorker } = useRegisterSW({
  onRegistered(r: ServiceWorkerRegistration | undefined) {
    // Check for updates every hour
    if (r) {
      setInterval(() => {
        r.update()
      }, 3600000)
    }
  },
  onOfflineReady() {
    console.log('App ready to work offline')
  },
})

// Auto-trigger update when detected
watch(needRefresh, (newVal) => {
  if (newVal) {
    updateServiceWorker(true)
  }
})

function updateApp() {
  updateServiceWorker(true)
}

onMounted(() => {
  fetchUserInfo()
})
</script>


<style>
.weather-icon {
  filter: brightness(0) invert(1);
}
</style>