<template>
  <div class="hero hero-bg min-h-screen">
    <div class="hero-overlay"></div>
    <div class="hero-content flex-col w-full max-w-sm px-4">
      <div class="card bg-base-100 w-full shadow-2xl">
        <div class="card-body p-6">
          <h2 class="card-title text-2xl mb-2">{{ t('forgot_password') }}</h2>

          <div v-if="submitted" class="alert alert-success">
            <span>{{ t('reset_email_sent') }}</span>
          </div>

          <template v-else>
            <p class="text-sm text-base-content/70 mb-4">{{ t('forgot_password_desc') }}</p>
            <fieldset class="fieldset">
              <label class="label text-sm">{{ t('email') }}</label>
              <input
                type="email"
                v-model="email"
                :placeholder="t('email')"
                class="input input-bordered w-full"
                @keyup.enter="requestReset"
              />
              <button
                class="btn btn-primary mt-4 w-full"
                :disabled="loading || !email"
                @click="requestReset"
              >
                {{ t('send_reset_link') }}
                <span v-if="loading" class="loading loading-spinner loading-md ml-4"></span>
              </button>
            </fieldset>
          </template>

          <div class="mt-4 text-center">
            <router-link to="/public/login" class="link link-hover text-sm">
              {{ t('back_to_login') }}
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTranslation } from '../composables/useTranslation'

const { t } = useTranslation()
const email = ref('')
const loading = ref(false)
const submitted = ref(false)

async function requestReset() {
  if (!email.value) return
  loading.value = true
  try {
    await fetch('/api/public/request-reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ email: email.value }),
    })
    // Always show the same success message regardless of outcome (prevent enumeration)
    submitted.value = true
  } catch {
    submitted.value = true
  } finally {
    loading.value = false
  }
}
</script>
