<template>
  <div class="navbar bg-base-100 shadow-sm rounded-b p-4 md:p-0 lg:p-2">
    <div class="navbar-start">
      <!-- Mobile Menu -->
      <a href="/" class="btn btn-neutral text-3xl font-bold mx-4">
        WAQD
      </a>
    </div>
    <div class="navbar-center hidden md:flex"></div>
    <div class="navbar-end hidden md:flex">
      <!-- Desktop Menu -->
    </div>
  </div>

  <div class="hero hero-bg rounded-box min-h-[85vh]">
    <div class="hero-overlay"></div>
    <div class="hero-content flex-col">
        <div class="text-center lg:text-left glass rounded-box p-4 bg-primary">
            <h1 class="text-5xl font-bold">Coming soon!</h1>
            <p class="py-6 text-lg">
                Hook up your <a class="link text-purple-300"
                    href=" https://github.com/goszpeti/weather_air_quality_device">WAQD</a> device and monitor your data remotely.
            </p>
            
        </div>
        <div class="card bg-base-100 w-full max-w-lg1 shrink-0 shadow-2xl">
            <div class="card-body">
                    <p class="py-6 text text-center">
                        🗲 Powered by
                        <a class="link text-purple-300"
                            href=" https://github.com/goszpeti/weather_air_quality_device">WeatherAirQualityDevice
                            project@GitHub</a>
                    </p>
            </div>
        </div>
    </div>
  </div>


  <div class="flex-none">
    <button class="btn btn-ghost" @click="toggleTheme">
      Theme: {{ theme }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
// import heroBg from '@static/gui_base/pascal-debrunner-UjyUlxr1Yjo-unsplash.avif'
// import visibilityIcon from '@static/general_icons/visibility.svg'

const t = (k: string) => k // temporary stub so {{ t(...) }} doesn’t crash

const count = ref(0)
const theme = ref<'light' | 'dark'>('light')

function increment() {
  count.value++
}

function applyTheme() {
  document.documentElement.setAttribute('data-theme', theme.value)
}

function toggleTheme() {
  const themes = ['purple', 'teal', 'peach', 'orange', 'forest', 'red', 'light', 'dark']
  const currentIndex = themes.indexOf(theme.value)
  theme.value = themes[(currentIndex + 1) % themes.length]
  applyTheme()
}

onMounted(() => {
  applyTheme()
})

function login() {
  const loading = document.getElementById('loading') as HTMLElement | null
  const usernameInput = document.getElementById('username') as HTMLInputElement | null
  const passwordInput = document.getElementById('password') as HTMLInputElement | null

  if (!loading || !usernameInput || !passwordInput) {
    console.error('Missing DOM elements for login')
    return
  }

  loading.classList.remove('hidden')

  const username = usernameInput.value
  const password = passwordInput.value

  fetch('/public/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'password',
      username,
      password,
    }),
  })
    .then((response) => {
      if (!response.ok) {
        const toastsContainer = document.getElementById('toasts')
        if (toastsContainer) {
          const id = toastsContainer.children.length
          fetch(`toast/login_failed?id=${id}`)
            .then((r) => (r.ok ? r.text() : null))
            .then((html) => {
              if (!html) return
              const tempDiv = document.createElement('div')
              tempDiv.innerHTML = html
              toastsContainer.appendChild(tempDiv)
            })
            .catch((e) => console.error('Toast fetch error', e))
        }
        throw new Error('Login failed! Wrong username or password.')
      }

      return response.json()
    })
    .then((data) => {
      console.log('Success:', data)
      window.location.href = '/weather'
    })
    .catch((error) => {
      console.error('Error:', error)
    })
    .finally(() => {
      loading.classList.add('hidden')
    })
}
</script>
