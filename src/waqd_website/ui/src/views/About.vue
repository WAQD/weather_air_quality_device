<template>
  <div class="flex flex-col justify-center align-middle items-center min-h-[80vh] p-8">
    <img :src="iconUrl" class="h-28 mx-auto py-3" alt="WAQD Icon">
    <h1 class="pt-4 text-2xl">WeatherAirQualityDevice Website</h1>

    <h2 class="text-2xl p-2">{{ t('about_used_software') }}</h2>
    <div class="text-xl p-2 flex-col">
      <li>🗲 Powered by
        <a class="link link-accent" href="https://www.python.org/">Python</a>, with
        <a class="link link-accent" href="https://fastapi.tiangolo.com/">FastAPI</a>, and
        <a class="link link-accent" href="https://mariadb.org/">MariaDB</a> +
        <a class="link link-accent" href="https://www.sqlalchemy.org/">SQLAlchemy</a>
      </li>
      <li>Frontend built with
        <a class=" link link-accent" href="https://vuejs.org/">Vue.js</a> +
        <a class="link link-accent" href="https://tailwindcss.com/">Tailwind CSS</a> +
        <a class="link link-accent" href="https://daisyui.com/">DaisyUI</a> +
        <a class="link link-accent" href="https://www.highcharts.com/">Highcharts</a>
      </li>
      <li>{{ t('about_further_software') }}
        <a class="link link-accent" href=" https://github.com/goszpeti/WeatherAirQualityDevice">
          WeatherAirQualityDevice</a> {{ t('about_on_github') }}
      </li>
    </div>

    <h2 class="text-2xl p-2">{{ t('about_used_assets') }}</h2>
    <ul class="text-xl p-2 flex flex-col space-y-2 max-w-4xl">
      <li>
        {{ t('about_weather_icons') }}
        <a class="link link-accent" href="http://scripts.sil.org/OFL">SIL OFL 1.1</a>
        {{ t('about_from') }}
        <a class="link link-accent"
          href="https://github.com/erikflowers/weather-icons">weather-icons</a>
        {{ t('about_on_github') }}
      </li>
      <li>
        {{ t('about_franzo_font') }}
        <a class="link link-accent" href="https://www.apache.org/licenses/LICENSE-2.0">Apache
          2.0</a>
        {{ t('about_from') }}
        <a class="link link-accent" href="https://fontlibrary.org/en/font/franzo">Fontlibrary</a>
      </li>
      <li>
        {{ t('about_unsplash_images') }}
        <a class="link link-accent" href="https://unsplash.com/license">Unsplash license</a>
        {{ t('about_from') }}
        <a class="link link-accent" href="https://unsplash.com">Unsplash</a>
      </li>
    </ul>

    <h2 class="text-2xl p-2 mt-4">Copyright (c) 2026 Péter Gosztolya and contributors.</h2>
  </div>
</template>

<script setup lang="ts">
import { useTranslation } from '../composables/useTranslation'

const { t } = useTranslation()
const iconUrl = '/static/gui_base/icon.avif'
</script>
