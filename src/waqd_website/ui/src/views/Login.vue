<template>
  <div>
    <!-- Toast Container -->
    <div class="toast toast-top toast-end z-50">
      <div v-if="showLoginFailedToast" class="alert alert-error">
        <span>{{ t('login_failed') }}</span>
        <button class="btn btn-square btn-error" @click="showLoginFailedToast = false">
          <svg viewBox="0 0 24 24" class="h-4">
            <use :href="cancelIconUrl" fill="black" />
          </svg>
        </button>
      </div>
    </div>

    <div class="hero hero-bg rounded-box min-h-[85vh]">
      <div class="hero-overlay"></div>
      <div class="hero-content flex-col lg:flex-row">
      <div class="text-center lg:text-left glass rounded-box p-4 bg-primary">
        <h1 class="text-5xl font-bold">{{ t('login_now') }}</h1>
        <p class="py-6 text-lg">
          {{ t('login_web_access') }}
        </p>
      </div>
      <div class="card bg-base-100 w-full max-w-sm shrink-0 shadow-2xl">
        <div class="card-body">
          <fieldset class="fieldset text-2xl">
            <label class="label">{{ t('username') }}</label>
            <input
              type="text"
              id="username"
              v-model="username"
              name="username"
              autocomplete="username"
              :placeholder="t('username')"
              class="input input-bordered"
              @keyup.enter="login"
            />

            <label class="label">{{ t('password') }}</label>

            <div class="flex items-center">
              <input
                :type="passwordVisible ? 'text' : 'password'"
                id="password"
                v-model="password"
                class="input input-bordered flex-grow"
                autocomplete="password"
                :placeholder="t('password')"
                @keyup.enter="login"
              />
              <button
                type="button"
                class="btn btn-square ml-2"
                @click="togglePasswordVisibility"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 24 24">
                  <use :href="visibilityIconUrl" fill="white" />
                </svg>
              </button>
            </div>
            <!-- <div><a class="link link-hover">Forgot password?</a></div> -->
            <button class="btn btn-primary mt-4 text-lg" @click="login">
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
      router.push('/devices')
    })
    .catch((error) => {
      console.error('Error:', error)
    })
    .finally(() => {
      loading.value = false
    })
}
</script>


