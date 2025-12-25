<template>
  <div class="scroll-container">
    <!-- Main Hero Section -->
    <div class="hero hero-bg-main min-h-screen snap-section">
      <div class="hero-overlay bg-opacity-60"></div>
      <div class="hero-content flex-col max-w-4xl w-full relative z-10">
        <!-- Logged In View -->
        <div v-if="isLoggedIn"
          class="text-center glass rounded-box p-8 bg-primary/80 backdrop-blur-sm">
          <h1 class="text-5xl font-bold">Welcome back, {{ username }}!</h1>
          <p class="py-6 text-lg">
            Manage your
            <a class="link text-purple-300"
              href="https://github.com/goszpeti/weather_air_quality_device">
              WAQD
            </a>
            devices and monitor your data remotely.
          </p>
          <router-link to="/rest/devices" class="btn btn-secondary btn-lg">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" viewBox="0 0 20 20"
              fill="currentColor">
              <path
                d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
            </svg>
            Go to My Devices
          </router-link>
        </div>

        <!-- Not Logged In View -->
        <div v-else class="text-center glass rounded-box p-8 bg-primary/80 backdrop-blur-sm">
          <h1 class="text-5xl font-bold">Build Your Own Weather Station!</h1>
          <p class="py-6 text-lg">
            Create a professional indoor weather and air quality monitoring station with Raspberry
            Pi
          </p>
          <router-link to="/public/login" class="btn btn-secondary btn-lg">Get Started</router-link>
        </div>
      </div>
    </div>

    <!-- Features Hero Section -->
    <div class="hero hero-bg-features min-h-screen snap-section">
      <div class="hero-overlay bg-opacity-70"></div>
      <div class="hero-content flex-row max-w-7xl w-full gap-6 px-8 relative z-10">
        <div class="w-2/5 flex justify-center">
          <img :src="mainGuiImg" alt="WAQD Main Interface"
            class="rounded-lg shadow-2xl max-w-md w-full" />
        </div>
        <div class="w-3/5 glass rounded-box p-6 bg-base-100/90 backdrop-blur-sm">
          <h2 class="text-3xl font-bold mb-4">Full-Featured Display</h2>
          <ul class="space-y-2 text-base">
            <li class="flex items-start">
              <span class="text-xl mr-2">🕐</span>
              <span>Real-time clock and date display</span>
            </li>
            <li class="flex items-start">
              <span class="text-xl mr-2">🌡️</span>
              <span>Interior temperature, humidity, and pressure from sensors</span>
            </li>
            <li class="flex items-start">
              <span class="text-xl mr-2">🌤️</span>
              <span>Exterior weather from online services or remote sensors</span>
            </li>
            <li class="flex items-start">
              <span class="text-xl mr-2">📅</span>
              <span>3-day weather forecast at a glance</span>
            </li>
            <li class="flex items-start">
              <span class="text-xl mr-2">💨</span>
              <span>Air quality monitoring (CO2, TVOC)</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Hardware Hero Section -->
    <div class="hero hero-bg-hardware min-h-screen snap-section">
      <div class="hero-overlay bg-opacity-70"></div>
      <div class="hero-content flex-row max-w-7xl w-full gap-6 px-8 relative z-10">
        <div class="w-1/3 flex justify-center">
          <img :src="waqdStationImg" alt="WAQD Station"
            class="rounded-lg shadow-2xl max-w-xs w-full" />
        </div>
        <div class="w-2/3 glass rounded-box p-6 bg-base-100/90 backdrop-blur-sm">
          <h2 class="text-3xl font-bold mb-4">Easy Assembly</h2>
          <p class="text-base mb-3">
            Built with readily available components and a recommended case design for clean cable
            management.
          </p>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-base-200 rounded-lg p-3">
              <h3 class="font-bold text-base mb-1">🔧 Raspberry Pi</h3>
              <p class="text-sm">All versions supporting ARMv7 64-bit</p>
            </div>
            <div class="bg-base-200 rounded-lg p-3">
              <h3 class="font-bold text-base mb-1">📺 Display</h3>
              <p class="text-sm">Raspberry Pi 7" touchscreen or Waveshare 5"</p>
            </div>
            <div class="bg-base-200 rounded-lg p-3">
              <h3 class="font-bold text-base mb-1">🌡️ Sensors</h3>
              <p class="text-sm">BME280, MH-Z19, CCS811, DHT22, PIR501</p>
            </div>
            <div class="bg-base-200 rounded-lg p-3">
              <h3 class="font-bold text-base mb-1">📦 Case</h3>
              <p class="text-sm">SmartiPi Touch 2 recommended</p>
            </div>
          </div>
          <p href="https://github.com/WAQD/weather_air_quality_device/wiki/Assembly-and-Software-Setup-Guide"
            target="_blank" class="link font-semibold ml-1 mt-4 inline-block">
            View full assembly guide
          </p>
        </div>
      </div>
    </div>

    <!-- 3D Printable Case Hero Section -->
    <div class="hero hero-bg-3dprint min-h-screen snap-section">
      <div class="hero-overlay bg-opacity-70"></div>
      <div class="hero-content flex-row max-w-7xl w-full gap-6 px-8 relative z-10">
        <div class="w-2/5 flex justify-center">
          <img :src="sensorCaseImg" alt="3D Printable Sensor Case"
            class="rounded-lg shadow-2xl max-w-sm w-full" />
        </div>
        <div class="w-3/5 glass rounded-box p-6 bg-base-100/90 backdrop-blur-sm">
          <h2 class="text-3xl font-bold mb-4">3D Printable Sensor Case</h2>
          <p class="text-base mb-3">
            Custom designed sensor housing that mounts perfectly on the back of the SmartiPi Touch 2
            case.
          </p>
          <ul class="space-y-2 text-base">
            <li class="flex items-start">
              <span class="text-xl mr-2">📦</span>
              <span>Holds up to 4 sensors with optimized spacing</span>
            </li>
            <li class="flex items-start">
              <span class="text-xl mr-2">💨</span>
              <span>Ventilation slits for accurate air quality readings</span>
            </li>
            <li class="flex items-start">
              <span class="text-xl mr-2">🔌</span>
              <span>Cable routing holes for clean installation</span>
            </li>
            <li class="flex items-start">
              <span class="text-xl mr-2">🔩</span>
              <span>Requires just 4 M3x30 screws for mounting</span>
            </li>
          </ul>
          <div class="mt-4">
            <p class="text-sm opacity-70">STL files available in the project repository</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Customization Hero Section -->
    <div class="hero hero-bg-custom min-h-screen snap-section">
      <div class="hero-overlay bg-opacity-70"></div>
      <div class="hero-content flex-row max-w-7xl w-full gap-6 px-8 relative z-10">
        <div class="w-2/5 flex justify-center">
          <img :src="optionsImg" alt="WAQD Options" class="rounded-lg shadow-2xl max-w-md w-full" />
        </div>
        <div class="w-3/5 glass rounded-box p-6 bg-base-100/90 backdrop-blur-sm">
          <h2 class="text-3xl font-bold mb-4">Fully Customizable</h2>
          <p class="text-base mb-4">
            Tailor your weather station to your preferences with extensive configuration options.
          </p>
          <div class="grid grid-cols-2 gap-3">
            <div class="card bg-base-200 shadow-xl">
              <div class="card-body p-4">
                <h3 class="card-title text-base">🌍 Location</h3>
                <p class="text-sm">Set your location for accurate forecasts</p>
              </div>
            </div>
            <div class="card bg-base-200 shadow-xl">
              <div class="card-body p-4">
                <h3 class="card-title text-base">🎨 Display</h3>
                <p class="text-sm">Brightness, sleep mode, themes</p>
              </div>
            </div>
            <div class="card bg-base-200 shadow-xl">
              <div class="card-body p-4">
                <h3 class="card-title text-base">🌐 Language</h3>
                <p class="text-sm">Multiple language support</p>
              </div>
            </div>
            <div class="card bg-base-200 shadow-xl">
              <div class="card-body p-4">
                <h3 class="card-title text-base">☁️ Weather</h3>
                <p class="text-sm">Online weather service settings</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Call to Action Section -->
    <div class="hero hero-bg-cta min-h-[60vh] snap-section">
      <div class="hero-overlay bg-opacity-60"></div>
      <div class="hero-content text-center max-w-4xl relative z-10">
        <div class="glass rounded-box p-12 bg-primary/80 backdrop-blur-sm">
          <h2 class="text-5xl font-bold mb-6">Ready to Start Building?</h2>
          <p class="text-xl mb-8">
            Build your own weather station and register for remote monitoring today!
          </p>
          <div class="flex flex-col sm:flex-row gap-4 justify-center">
            <a href="https://github.com/goszpeti/weather_air_quality_device" target="_blank"
              class="btn btn-secondary btn-lg">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" viewBox="0 0 24 24"
                fill="currentColor">
                <path
                  d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              View on GitHub
            </a>
            <router-link to="/public/about" class="btn btn-primary btn-secondary btn-lg">
              {{ t('settings_tab_about') }}
            </router-link>
          </div>
          <p class="mt-8 text-sm opacity-80">
            🗲 Open Source Project under AGPL-3.0 License
          </p>
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

// Image URLs - defined as constants to prevent Vite from resolving as imports
const mainGuiImg = '/static/doc_images/main_gui.png'
const waqdStationImg = '/static/doc_images/waqd_station.jpg'
const sensorCaseImg = '/static/doc_images/sensor_case.png'
const optionsImg = '/static/doc_images/options.png'
</script>

<style scoped>
.scroll-container {
  scroll-snap-type: y mandatory;
  overflow-y: scroll;
  height: 100vh;
}

.snap-section {
  scroll-snap-align: start;
  scroll-snap-stop: always;
}

.hero-bg-main {
  background-image: url(/static/gui_base/pascal-debrunner-UjyUlxr1Yjo-unsplash.avif);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.hero-bg-features {
  background-image: url(/static/gui_base/wolfgang-hasselmann-bR_-gllg7Bs-unsplash.avif);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.hero-bg-hardware {
  background-image: url(/static/gui_base/ish-consul-Ozlzi3DXuGg-unsplash.avif);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.hero-bg-3dprint {
  background-image: url(/static/gui_base/miguel-dias-coelho-ZbGwGW_u8zI-unsplash.avif);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.hero-bg-custom {
  background-image: url(/static/gui_base/joe-r-harris-KOnl4LFvwHE-unsplash.avif);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.hero-bg-cta {
  background-image: url(/static/gui_base/gaspar-uhas-Y3vsGbFCX-o-unsplash.avif);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
</style>
