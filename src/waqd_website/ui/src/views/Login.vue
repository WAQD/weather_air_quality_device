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

    <div class="hero hero-bg min-h-[95vh]">
      <div class="hero-overlay"></div>
      <div class="hero-content flex-col lg:flex-row px-2 sm:px-6 lg:px-8 max-w-full gap-4 sm:gap-8">
      <div class="text-center lg:text-left glass rounded-box p-3 sm:p-4 bg-primary w-full max-w-[calc(100vw-1rem)] sm:max-w-[calc(100vw-2rem)] lg:w-auto lg:max-w-none">
        <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold">{{ t('login_now') }}</h1>
        <p class="py-4 sm:py-6 text-base sm:text-lg">
          {{ t('login_web_access') }}
        </p>
      </div>
      <div class="card bg-base-100 w-full max-w-[calc(100vw-1rem)] sm:max-w-sm shrink-0 shadow-2xl">
        <div class="card-body p-3 sm:p-6 lg:p-8">
          <fieldset class="fieldset text-lg sm:text-2xl">
            <label class="label text-sm sm:text-base">{{ t('username') }}</label>
            <input
              type="text"
              id="username"
              v-model="username"
              name="username"
              autocomplete="username"
              :placeholder="t('username')"
              class="input input-bordered text-sm sm:text-base"
              @keyup.enter="login"
            />

            <label class="label text-sm sm:text-base">{{ t('password') }}</label>

            <div class="flex items-center">
              <input
                :type="passwordVisible ? 'text' : 'password'"
                id="password"
                v-model="password"
                class="input input-bordered flex-grow text-sm sm:text-base"
                autocomplete="password"
                :placeholder="t('password')"
                @keyup.enter="login"
              />
              <button
                type="button"
                :class="['btn btn-square ml-1 sm:ml-2 min-h-0 h-12', { 'btn-active btn-primary': passwordVisible }]"
                @click="togglePasswordVisibility"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 sm:h-6 sm:w-6" viewBox="0 0 24 24">
                  <use :href="visibilityIconUrl" fill="white" />
                </svg>
              </button>
            </div>
            <!-- <div><a class="link link-hover">Forgot password?</a></div> -->
            <button class="btn btn-primary mt-4 text-base sm:text-lg" @click="login">
              {{ t('login') }}
              <span v-if="loading" class="loading loading-spinner loading-md ml-4"></span>
            </button>
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
const cancelIconUrl = '/static/general_icons/cancel.svg#main'
const username = ref('')
const password = ref('')
const loading = ref(false)
const passwordVisible = ref(false)
const showLoginFailedToast = ref(false)

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
      router.push('/rest/devices')
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

