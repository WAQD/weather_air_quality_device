<template>
  <div class="hero hero-bg rounded-box min-h-[85vh]">
    <div class="hero-overlay"></div>
    <div class="hero-content flex-col">
      <div class="text-center lg:text-left glass rounded-box p-4 bg-primary">
        <h1 class="text-5xl font-bold">Coming soon!</h1>
        <p class="py-6 text-lg">
          Hook up your
          <a
            class="link text-purple-300"
            href="https://github.com/goszpeti/weather_air_quality_device"
          >
            WAQD
          </a>
          device and monitor your data remotely.
        </p>
      </div>
      <div class="card bg-base-100 w-full max-w-lg1 shrink-0 shadow-2xl">
        <div class="card-body">
          <p class="py-6 text text-center">
            🗲 Powered by
            <a
              class="link text-purple-300"
              href="https://github.com/goszpeti/weather_air_quality_device"
            >
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

const { t } = useTranslation()
</script>

<style scoped>
.hero-bg {
  background-image: url(/static/gui_base/pascal-debrunner-UjyUlxr1Yjo-unsplash.avif);
}
</style>
