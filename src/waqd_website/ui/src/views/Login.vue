<template>
  <div class="overflow-x-hidden">
    <!-- Toast Container -->
    <div class="toast toast-bottom toast-end z-50">
      <div v-if="showLoginFailedToast" class="alert alert-error">
        <span>{{ t('login_failed') }}</span>
        <button class="btn btn-square btn-error" @click="showLoginFailedToast = false">
          <svg viewBox="0 0 24 24" class="h-4">
            <use :href="cancelIconUrl" fill="black" />
          </svg>
        </button>
      </div>
    </div>
    <!-- Beta Warning Alert -->
    <div class="alert alert-warning shadow-lg w-full">
      <svg class="stroke-current shrink-0 h-6 w-6">
        <use :href="warningIconUrl" fill="currentColor" />
      </svg>
      <div>
        <h3 class="font-bold">{{ t('closed_beta') }}</h3>
        <div class="text-xs">{{ t('closed_beta_desc') }}</div>
      </div>
    </div>
    <div class="hero hero-bg min-h-[95vh]">
      <div class="hero-overlay"></div>

      <div class="hero-content flex-col lg:flex-row px-2 sm:px-6 lg:px-8 max-w-full gap-4 sm:gap-8">
        <div
          class="text-center lg:text-left glass rounded-box p-3 sm:p-4 bg-primary w-full max-w-[calc(100vw-1rem)] sm:max-w-[calc(100vw-2rem)] lg:w-auto lg:max-w-none">
          <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold">{{ t('login_now') }}</h1>
          <p class="py-4 sm:py-6 text-base sm:text-lg">
            {{ t('login_web_access') }}
          </p>
        </div>

        <div
          class="card bg-base-100 w-full max-w-[calc(100vw-1rem)] sm:max-w-sm shrink-0 shadow-2xl">
          <div class="card-body p-3 sm:p-6 lg:p-8">
            <fieldset class="fieldset text-lg sm:text-2xl">
              <label class="label text-sm sm:text-base">{{ t('username') }}</label>
              <input type="text" id="username" v-model="username" name="username"
                autocomplete="username" :placeholder="t('username')"
                class="input input-bordered w-full text-sm sm:text-base" @keyup.enter="login" />

              <label class="label text-sm sm:text-base">{{ t('password') }}</label>

              <div class="join w-full">
                <input :type="passwordVisible ? 'text' : 'password'" id="password"
                  v-model="password"
                  class="join-item input input-bordered w-full text-sm sm:text-base"
                  autocomplete="password" :placeholder="t('password')" @keyup.enter="login" />
                <button type="button"
                  :class="['join-item btn min-h-0', { 'btn-active btn-primary': passwordVisible }]"
                  @click="togglePasswordVisibility" aria-label="Toggle password visibility">
                  <svg class="h-6 w-6">
                    <use :href="passwordVisible ? visibilityOffIconUrl : visibilityIconUrl"
                      fill="currentColor" />
                  </svg>
                </button>
              </div>
              <div class="text-left mt-1">
                <label class="flex items-center justify-start text-xs sm:text-sm gap-2">
                  <input type="checkbox" v-model="rememberMe" class="checkbox h-4 w-4" />
                  <span class="label-text">{{ t('remember_me_30_days') }}</span>
                </label>
              </div>
              <div class="flex flex-col gap-3 mt-4">
                <button class="btn btn-primary w-full text-base sm:text-lg" @click="login">
                  {{ t('login') }}
                  <span v-if="loading" class="loading loading-spinner loading-md ml-4"></span>
                </button>
                <router-link to="/public/forgot-password"
                  class="link link-hover text-sm text-center">
                  {{ t('forgot_password') }}
                </router-link>
                <router-link v-if="enableSignup" to="/public/signup"
                  class="btn btn-primary w-full text-base sm:text-lg">
                  {{ t('create_account') }}
                </router-link>
              </div>
            </fieldset>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'
import { useUser } from '../composables/useUser'

const router = useRouter()
const { t } = useTranslation()
const { fetchUserInfo } = useUser()

const visibilityIconUrl = '/static/general_icons/visibility.svg#main'
const visibilityOffIconUrl = '/static/general_icons/visibility_off.svg#main'
const cancelIconUrl = '/static/general_icons/cancel.svg#main'
const warningIconUrl = '/static/general_icons/warning.svg#main'
const enableSignup = __ENABLE_SIGNUP__
const username = ref('')
const password = ref('')
const loading = ref(false)
const passwordVisible = ref(false)
const showLoginFailedToast = ref(false)
const rememberMe = ref(false)

// Auto-hide toast after 5 seconds
watch(showLoginFailedToast, (newValue) => {
  if (newValue) {
    setTimeout(() => {
      showLoginFailedToast.value = false
    }, 5000)
  }
})

function togglePasswordVisibility() {
  passwordVisible.value = !passwordVisible.value
}

function login() {
  loading.value = true

  fetch('/api/public/token', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'password',
      username: username.value,
      password: password.value,
      remember_me: rememberMe.value ? 'true' : 'false',
    }),
  })
    .then((response) => {
      if (!response.ok) {
        showLoginFailedToast.value = true
        throw new Error('Login failed! Wrong username or password.')
      }

      return response.json()
    })
    .then(async (data) => {
      console.log('Success:', data)
      await fetchUserInfo()
      router.push('/home')
    })
    .catch((error) => {
      console.error('Error:', error)
    })
    .finally(() => {
      loading.value = false
    })
}
</script>

<style scoped>
/* Override DaisyUI hero-content min-width on mobile */
@media (max-width: 640px) {
  .hero-content {
    min-width: auto !important;
    max-width: 100vw !important;
  }
}
</style>
