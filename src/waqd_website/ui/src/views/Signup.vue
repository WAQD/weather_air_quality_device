<template>
  <div class="hero hero-bg min-h-screen">
    <div class="hero-overlay"></div>
    <div class="hero-content flex-col w-full max-w-sm px-4">
      <div class="card bg-base-100 w-full shadow-2xl">
        <div class="card-body p-6">
          <h2 class="card-title text-2xl mb-2">{{ t('create_account') }}</h2>
          <div v-if="submitted" class="alert alert-success">
            <span>{{ t('signup_check_email') }}</span>
          </div>
          <template v-else>
            <p v-if="error" class="alert alert-error mb-4">{{ error }}</p>
            <fieldset class="fieldset">
              <label class="label">{{ t('username') }}</label>
              <input v-model.trim="username" type="text" autocomplete="username"
                class="input input-bordered w-full" :placeholder="t('username')" />
              <label class="label">{{ t('email') }}</label>
              <input v-model.trim="email" type="email" autocomplete="email"
                class="input input-bordered w-full" :placeholder="t('email')" />
              <label class="label">{{ t('password') }}</label>
              <input v-model="password" type="password" autocomplete="new-password"
                class="input input-bordered w-full" :placeholder="t('password')" />
              <label class="label">{{ t('confirm_password') }}</label>
              <input v-model="passwordConfirmation" type="password" autocomplete="new-password"
                class="input input-bordered w-full" :placeholder="t('confirm_password')"
                @keyup.enter="signup" />
              <label class="label cursor-pointer justify-start gap-2 mt-2">
                <input v-model="acceptTerms" type="checkbox" class="checkbox" />
                <span class="label-text">{{ t('accept_terms') }}</span>
              </label>
              <button class="btn btn-primary mt-4 w-full" :disabled="loading" @click="signup">
                {{ t('create_account') }}
                <span v-if="loading" class="loading loading-spinner loading-md ml-4"></span>
              </button>
            </fieldset>
          </template>
          <div class="mt-4 text-center">
            <router-link to="/public/login" class="link link-hover text-sm">{{ t('back_to_login')
              }}</router-link>
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
const username = ref('')
const email = ref('')
const password = ref('')
const passwordConfirmation = ref('')
const acceptTerms = ref(false)
const loading = ref(false)
const submitted = ref(false)
const error = ref('')

async function signup() {
  error.value = ''
  if (!username.value || !email.value || !password.value || password.value !== passwordConfirmation.value || !acceptTerms.value) {
    error.value = t('signup_invalid_form')
    return
  }
  loading.value = true
  try {
    const response = await fetch('/api/public/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: username.value, email: email.value, password: password.value, password_confirmation: passwordConfirmation.value, accept_terms: 'true' })
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || t('signup_failed'))
    submitted.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : t('signup_failed')
  } finally {
    loading.value = false
  }
}
</script>
