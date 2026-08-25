<template>
  <div class="hero hero-bg min-h-screen">
    <div class="hero-overlay"></div>
    <div class="hero-content w-full max-w-sm px-4">
      <div class="card bg-base-100 w-full shadow-2xl">
        <div class="card-body p-6 text-center">
          <span v-if="loading" class="loading loading-spinner loading-lg mx-auto"></span>
          <div v-else :class="['alert', verified ? 'alert-success' : 'alert-error']">
            <span>{{ message }}</span>
          </div>
          <router-link to="/public/login" class="btn btn-primary mt-4">{{ t('back_to_login')
            }}</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'

const { t } = useTranslation()
const route = useRoute()
const loading = ref(true)
const verified = ref(false)
const message = ref('')

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) {
    message.value = t('verification_invalid')
    loading.value = false
    return
  }
  try {
    const response = await fetch('/api/public/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ token })
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || t('verification_invalid'))
    verified.value = true
    message.value = data.detail
  } catch (err) {
    message.value = err instanceof Error ? err.message : t('verification_invalid')
  } finally {
    loading.value = false
  }
})
</script>
