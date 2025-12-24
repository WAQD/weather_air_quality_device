<template>
  <div class="hero hero-bg min-h-screen">
    <div class="hero-overlay bg-opacity-60"></div>
    <div class="hero-content flex-col max-w-4xl w-full relative z-10">
      <!-- Logged In View -->
      <div v-if="isLoggedIn" class="text-center glass rounded-box p-8 bg-primary/80 backdrop-blur-sm">
        <h1 class="text-5xl font-bold">Welcome back, {{ username }}!</h1>
        <p class="py-6 text-lg">
          Manage your
          <a class="link text-purple-300"
            href="https://github.com/goszpeti/weather_air_quality_device">
            WAQD
          </a>
          devices and monitor your data remotely.
        </p>
        <router-link to="/devices" class="btn btn-secondary btn-lg">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
          Go to My Devices
        </router-link>
      </div>

      <!-- Not Logged In View -->
      <div v-else class="text-center glass rounded-box p-8 bg-primary/80 backdrop-blur-sm">
        <h1 class="text-5xl font-bold">Register now!</h1>
        <p class="py-6 text-lg">
          Hook up your
          <a class="link text-purple-300"
            href="https://github.com/goszpeti/weather_air_quality_device">
            WAQD
          </a>
          device and monitor your data remotely.
        </p>
        <router-link to="/login" class="btn btn-secondary btn-lg">Get Started</router-link>
      </div>

      <div class="card bg-base-100/90 backdrop-blur-sm w-full shadow-2xl mt-8">
        <div class="card-body">
          <p class="py-6 text-lg text-center">
            🗲 Powered by
            <a class="link text-purple-300"
              href="https://github.com/goszpeti/weather_air_quality_device">
              WeatherAirQualityDevice project@GitHub
            </a>
          </p>
          <div class="flex justify-center mt-4">
            <router-link to="/about" class="btn btn-outline btn-primary">
              {{ t('settings_tab_about') }}
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useTranslation } from '../composables/useTranslation'
import { useUser } from '../composables/useUser'

const { t } = useTranslation()
const { isLoggedIn, username } = useUser()
</script>

<style scoped>
.hero-bg {
  background-image: url(/static/gui_base/pascal-debrunner-UjyUlxr1Yjo-unsplash.avif);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
</style>
