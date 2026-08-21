<template>
  <div
    class="navbar bg-base-100 shadow-sm p-4 md:p-0 lg:p-2 sticky top-0 z-50 flex-wrap md:flex-nowrap">
    <!-- Toast Container -->
    <div class="toast toast-bottom toast-end z-50">
      <div v-if="showLogoutToast" class="alert alert-success">
        <span>{{ t('logout_success') }}</span>
        <button class="btn btn-square btn-success" @click="showLogoutToast = false">
          <svg viewBox="0 0 24 24" class="h-4">
            <use :href="cancelIconUrl" fill="currentColor" />
          </svg>
        </button>
      </div>
    </div>

    <div class="navbar-start gap-1">
      <!-- Hamburger Nav Menu -->
      <div v-if="isLoggedIn" class="dropdown dropdown-bottom z-50">
        <label tabindex="0" class="btn btn-ghost btn-circle btn-sm md:btn-md">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24"
            stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </label>
        <ul tabindex="0"
          class="dropdown-content menu p-2 shadow bg-base-200 rounded-box w-52 mt-4 text-base lg:text-lg">
          <li>
            <router-link to="/home">{{ t('home') }}</router-link>
          </li>
          <li>
            <router-link to="/public/home">{{ t('home_build_station') }}</router-link>
          </li>
          <li>
            <router-link to="/rest/devices">{{ t('my_devices') }}</router-link>
          </li>
          <li>
            <router-link to="/rest/weather">{{ t('home_weather') }}</router-link>
          </li>
        </ul>
      </div>
      <!-- Logo -->
      <router-link :to="isLoggedIn ? '/home' : '/public/home'"
        class="btn btn-primary text-xl md:text-3xl font-bold mx-1 md:mx-2">
        WAQD
      </router-link>
    </div>
    <div class="navbar-center flex-1 flex w-full order-last md:order-none md:w-auto mt-2 md:mt-0">
      <div id="search_bar"
        class="w-full basis-full md:flex-none md:w-[clamp(20rem,42vw,56rem)] px-0 md:px-4">
        <div v-if="isLoggedIn" class="w-full">
          <div class="dropdown dropdown-bottom w-full">
            <label
              class="input input-bordered input-sm lg:input-md flex items-center gap-2 w-full cursor-pointer">
              <svg viewBox="0 0 24 24" class="h-5 w-5 opacity-60 flex-shrink-0">
                <path fill="currentColor"
                  d="M10 2a8 8 0 105.293 14.293l4.707 4.707 1.414-1.414-4.707-4.707A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z" />
              </svg>
              <input v-model="weatherSearchQuery" type="search"
                :placeholder="t('home_weather_search_placeholder')" class="w-full lg:text-lg"
                :disabled="isSelectingLocation" @focus="openDropdown"
                @keydown.escape="closeDropdown" />
              <span v-if="isSearching || isSelectingLocation"
                class="loading loading-spinner loading-xs opacity-70"></span>
            </label>
            <ul v-if="dropdownOpen"
              class="dropdown-content menu flex flex-col flex-nowrap p-2 shadow bg-base-100 rounded-box w-full mt-1 max-h-96 overflow-y-auto overflow-x-hidden z-50">
              <!-- Saved Location Section -->
              <template v-if="hasSavedLocation && weatherSearchQuery.length === 0">
                <li class="menu-title">
                  <span>{{ t('home_weather_saved_location') }}</span>
                </li>
                <li v-for="location in displayedSavedLocations"
                  :key="`${location.latitude}-${location.longitude}`">
                  <button type="button" class="w-full text-left flex items-center gap-3"
                    :disabled="isSelectingLocation"
                    @mousedown.prevent="selectSavedLocation(location)" @click.prevent>
                    <img :src="getFlagIconUrl(location.country_code)" :alt="location.country_code"
                      class="w-5 h-4 rounded-sm" />
                    <div class="flex flex-col text-left">
                      <span class="font-semibold lg:text-base">{{ location.name }}</span>
                      <span class="text-xs lg:text-sm opacity-70">{{ location.state ||
                        location.country }}, {{
                          location.latitude.toFixed(2) }}, {{ location.longitude.toFixed(2) }}</span>
                    </div>
                    <span v-if="selectingLocationKey === getLocationKey(location)"
                      class="loading loading-spinner loading-xs ml-auto"></span>
                  </button>
                </li>
              </template>

              <!-- Search Results Section -->
              <li v-if="weatherSearchQuery.length >= 3 && displayedResults.length > 0"
                class="menu-title">
                <span>{{ t('search_results') }}</span>
              </li>
              <li v-for="(location, idx) in displayedResults" :key="idx">
                <button type="button" class="w-full text-left flex items-center gap-3"
                  :disabled="isSelectingLocation" @mousedown.prevent="selectLocation(location)"
                  @click.prevent>
                  <img :src="getFlagIconUrl(location.country_code)" :alt="location.country_code"
                    class="w-5 h-4 rounded-sm" />
                  <div class="flex flex-col text-left">
                    <span class="font-semibold lg:text-base">{{ location.name }}</span>
                    <span class="text-xs lg:text-sm opacity-70">{{ location.state ||
                      location.country }}, {{
                        location.latitude.toFixed(2) }}, {{ location.longitude.toFixed(2) }}</span>
                  </div>
                  <span v-if="selectingLocationKey === getLocationKey(location)"
                    class="loading loading-spinner loading-xs ml-auto"></span>
                </button>
              </li>

              <li v-if="weatherSearchQuery.length >= 3 && isSearching"
                class="text-center text-sm opacity-70 py-2">
                <span class="inline-flex items-center gap-2">
                  <span class="loading loading-spinner loading-xs"></span>
                  Searching locations...
                </span>
              </li>

              <li v-if="isSelectingLocation" class="text-center text-sm opacity-70 py-2">
                <span class="inline-flex items-center gap-2">
                  <span class="loading loading-spinner loading-xs"></span>
                  Loading weather for selected location...
                </span>
              </li>

              <!-- Prompt for search -->
              <li v-if="weatherSearchQuery.length === 0 && !hasSavedLocation"
                class="text-center text-sm opacity-70 py-2">
                <span>{{ t('home_weather_search_prompt') }}</span>
              </li>
              <li v-if="weatherSearchQuery.length > 0 && weatherSearchQuery.length < 3"
                class="text-center text-sm opacity-70 py-2">
                <span>{{ t('search_min_chars') }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

    </div>
    <div class="navbar-end flex gap-1 md:gap-0">
      <!-- Language Switcher -->
      <div class="dropdown dropdown-end z-50">
        <label tabindex="0" class="btn btn-outline btn-sm mx-1 md:mx-2">
          {{ locale.toUpperCase() }}
        </label>
        <ul tabindex="0"
          class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-32 mt-4 text-base lg:text-lg">
          <li><a @click="setLocale('en')">English</a></li>
          <li><a @click="setLocale('de')">Deutsch</a></li>
          <li><a @click="setLocale('hu')">Magyar</a></li>
        </ul>
      </div>
      <!-- User Menu -->
      <div class="dropdown dropdown-end z-50">
        <label tabindex="0" class="btn btn-ghost btn-circle btn-sm md:btn-md mx-1 md:mx-2">
          <svg viewBox="0 0 24 24" class="h-6 w-6 md:h-8 md:w-8">
            <use :href="accountIconUrl" fill="currentColor" />
          </svg>
        </label>
        <ul tabindex="0"
          class="dropdown-content menu p-2 shadow bg-base-200 rounded-box w-52 mt-4 text-base lg:text-lg">
          <li v-if="isLoggedIn" class="menu-title">
            <span>{{ username }}</span>
          </li>
          <li v-if="!isLoggedIn">
            <router-link to="/public/login" class="btn btn-ghost btn-sm lg:text-base">{{ t('login')
              }}</router-link>
          </li>
          <li v-if="isLoggedIn">
            <router-link to="/account" class="btn btn-ghost btn-sm lg:text-base">{{
              t('account_settings')
            }}</router-link>
          </li>
          <li v-if="isLoggedIn && isAdmin">
            <router-link to="/admin" class="btn btn-ghost btn-sm lg:text-base">{{
              t('admin_controls')
            }}</router-link>
          </li>
          <li v-if="isLoggedIn">
            <a @click="handleLogout" class="btn btn-ghost btn-sm lg:text-base ">{{ t('logout')
            }}</a>
          </li>
          <li>
            <a @click="toggleTheme" class="btn btn-ghost btn-sm lg:text-base capitalize">
              {{ t('theme') || 'Theme' }}: {{ t(theme) }}
            </a>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'
import { useUser } from '../composables/useUser'
import { useWebsiteWeather, type WeatherLocationPayload } from '../composables/useWebsiteWeather'

const router = useRouter()
const { t, locale, setLocale } = useTranslation()
const { isLoggedIn, username, isAdmin, logout: logoutUser } = useUser()
const {
  savedLocation,
  savedLocations,
  searchResults,
  searchLocations,
  cancelSearch,
  setCurrentLocation,
  loadWeatherForLocation,
  loadSavedLocation,
  isSearching,
  isLoadingWeather
} = useWebsiteWeather()

const theme = ref(localStorage.getItem('theme-preference') || 'system')
const showLogoutToast = ref(false)
const weatherSearchQuery = ref('')
const dropdownOpen = ref(false)
const selectingLocationKey = ref<string | null>(null)
const accountIconUrl = '/static/general_icons/account_circle.svg#main'
const cancelIconUrl = '/static/general_icons/cancel.svg#main'
let searchDebounce: number | null = null

const hasSavedLocation = computed(() => savedLocations.value.length > 0 || savedLocation.value !== null)
const displayedSavedLocations = computed(() => {
  if (savedLocations.value.length > 0) {
    return savedLocations.value.slice(0, 6)
  }

  return savedLocation.value ? [savedLocation.value] : []
})

const displayedResults = computed(() => {
  return searchResults.value.slice(0, 6)
})

const isSelectingLocation = computed(() => selectingLocationKey.value !== null && isLoadingWeather.value)

// Auto-hide logout toast after 5 seconds
watch(showLogoutToast, (newValue) => {
  if (newValue) {
    setTimeout(() => {
      showLogoutToast.value = false
    }, 5000)
  }
})

watch(weatherSearchQuery, (query) => {
  if (!isLoggedIn.value) {
    return
  }

  if (isSelectingLocation.value) {
    return
  }

  if (searchDebounce) {
    window.clearTimeout(searchDebounce)
  }

  if (query.length < 3) {
    cancelSearch()
    searchResults.value = []
    return
  }

  searchDebounce = window.setTimeout(() => {
    searchLocations(query, locale.value)
  }, 250)
})

function handleLogout() {
  logoutUser()
  weatherSearchQuery.value = ''
  showLogoutToast.value = true
  router.push('/')
}

function openDropdown() {
  dropdownOpen.value = true
}

function closeDropdown() {
  dropdownOpen.value = false
}

function getFlagIconUrl(countryCode: string): string {
  return `https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/7.3.2/flags/1x1/${countryCode.toLowerCase()}.svg`
}

function getLocationKey(location: WeatherLocationPayload): string {
  return `${location.latitude.toFixed(4)}:${location.longitude.toFixed(4)}`
}

async function selectLocationAndOpenWeather(location: WeatherLocationPayload): Promise<void> {
  selectingLocationKey.value = getLocationKey(location)
  weatherSearchQuery.value = ''
  setCurrentLocation(location)

  try {
    await router.push({ name: 'weather' })
    await loadWeatherForLocation(location)
    closeDropdown()
  } finally {
    selectingLocationKey.value = null
  }
}

async function selectSavedLocation(location: WeatherLocationPayload): Promise<void> {
  await selectLocationAndOpenWeather(location)
}

async function selectLocation(location: WeatherLocationPayload): Promise<void> {
  await selectLocationAndOpenWeather(location)
}

function applyTheme() {
  if (theme.value === 'system') {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
  } else {
    document.documentElement.setAttribute('data-theme', theme.value)
  }
}

function toggleTheme() {
  const themes = ['system', 'light', 'dark']
  const currentIndex = themes.indexOf(theme.value)
  const nextIndex = (currentIndex + 1) % themes.length
  theme.value = themes[nextIndex] || 'system'
  localStorage.setItem('theme-preference', theme.value)
  applyTheme()
}

onMounted(() => {
  applyTheme()
  // Listen for system theme changes if using system theme
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (theme.value === 'system') applyTheme()
  })

  if (isLoggedIn.value) {
    loadSavedLocation()
  }
})
</script>
