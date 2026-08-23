<template>
  <div class="hero hero-bg min-h-screen">
    <div class="hero-overlay"></div>
    <div class="hero-content flex-col w-full max-w-sm px-4">
      <div class="card bg-base-100 w-full shadow-2xl">
        <div class="card-body p-6">
          <h2 class="card-title text-2xl mb-2">{{ t('reset_password') }}</h2>

          <!-- No token in URL -->
          <div v-if="!token" class="alert alert-error">
            <span>{{ t('reset_token_missing') }}</span>
          </div>

          <!-- Success state -->
          <div v-else-if="success" class="alert alert-success">
            <span>{{ t('reset_password_success') }}</span>
            <router-link to="/public/login" class="btn btn-sm btn-ghost ml-2">
              {{ t('login') }}
            </router-link>
          </div>

          <!-- Form -->
          <template v-else>
            <div v-if="errorMsg" class="alert alert-error mb-2">
              <span>{{ errorMsg }}</span>
            </div>
            <fieldset class="fieldset">
              <label class="label text-sm">{{ t('new_password') }}</label>
              <div class="flex items-center">
                <input
                  :type="passwordVisible ? 'text' : 'password'"
                  v-model="newPassword"
                  :placeholder="t('new_password')"
                  class="input input-bordered flex-grow"
                  @keyup.enter="submitReset"
                />
                <button
                  type="button"
                  :class="['btn btn-square ml-2 min-h-0', { 'btn-active btn-primary': passwordVisible }]"
                  @click="passwordVisible = !passwordVisible"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24">
                    <use :href="visibilityIconUrl" fill="white" />
                  </svg>
                </button>
              </div>

              <label class="label text-sm mt-2">{{ t('confirm_password') }}</label>
              <input
                :type="passwordVisible ? 'text' : 'password'"
                v-model="confirmPassword"
                :placeholder="t('confirm_password')"
                class="input input-bordered w-full"
                @keyup.enter="submitReset"
              />

              <button
                class="btn btn-primary mt-4 w-full"
                :disabled="loading || !newPassword || !confirmPassword"
                @click="submitReset"
              >
                {{ t('reset_password') }}
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
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'

const { t } = useTranslation()
const route = useRoute()

const visibilityIconUrl = '/static/general_icons/visibility.svg#main'
const token = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordVisible = ref(false)
const loading = ref(false)
const success = ref(false)
const errorMsg = ref('')

onMounted(() => {
  token.value = (route.query.token as string) || ''
})

async function submitReset() {
  errorMsg.value = ''
  if (newPassword.value.length < 8) {
    errorMsg.value = t('password_too_short')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMsg.value = t('passwords_do_not_match')
    return
  }
  loading.value = true
  try {
    const response = await fetch('/api/public/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ token: token.value, new_password: newPassword.value }),
    })
    if (!response.ok) {
      const data = await response.json()
      errorMsg.value = data.detail || t('reset_token_invalid')
    } else {
      success.value = true
    }
  } catch {
    errorMsg.value = t('reset_token_invalid')
  } finally {
    loading.value = false
  }
}
</script>
