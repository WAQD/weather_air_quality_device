<template>
  <div class="navbar bg-base-100 shadow-sm rounded-b p-4 md:p-0 lg:p-2">
    <!-- Toast Container -->
    <div class="toast toast-top toast-end z-50">
      <div v-if="showLogoutToast" class="alert alert-success">
        <span>{{ t('logout_success') }}</span>
        <button class="btn btn-square btn-success" @click="showLogoutToast = false">
          <svg viewBox="0 0 24 24" class="h-4">
            <use :href="cancelIconUrl" fill="black" />
          </svg>
        </button>
      </div>
    </div>

    <div class="navbar-start">
      <!-- Mobile Menu -->
      <a href="/" class="btn btn-neutral text-3xl font-bold mx-4">
        WAQD
      </a>
    </div>
    <div class="navbar-center hidden md:flex"></div>
    <div class="navbar-end hidden md:flex">
      <!-- Theme toggle -->
      <div class="flex-none p-4">
        <button class="btn btn-ghost" @click="toggleTheme">
          Theme: {{ theme }}
        </button>
      </div>
      <!-- Language Switcher -->
      <div class="dropdown dropdown-end z-50">
        <label tabindex="0" class="btn btn-outline btn-sm mx-2">
          {{ locale.toUpperCase() }}
        </label>
        <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-32 mt-4">
          <li><a @click="setLocale('en')">English</a></li>
          <li><a @click="setLocale('de')">Deutsch</a></li>
          <li><a @click="setLocale('hu')">Magyar</a></li>
        </ul>
      </div>
      <!-- User Menu -->
      <div class="dropdown dropdown-end z-50">
        <label tabindex="0" class="btn btn-ghost btn-circle mx-2">
          <svg viewBox="0 0 24 24" class="h-8 w-8">
            <use :href="accountIconUrl" fill="currentColor" />
          </svg>
        </label>
        <ul tabindex="0" class="dropdown-content menu p-2 shadow bg-base-100 rounded-box w-52 mt-4">
          <li v-if="isLoggedIn" class="menu-title">
            <span>{{ username }}</span>
          </li>
          <li v-if="!isLoggedIn">
            <router-link to="/login">{{ t('login') }}</router-link>
          </li>
          <li v-if="isLoggedIn && isAdmin">
            <router-link to="/admin">{{ t('admin_controls') }}</router-link>
          </li>
          <li v-if="isLoggedIn">
            <a @click="handleLogout">{{ t('logout') }}</a>
          </li>
        </ul>
      </div>
    </div>
  </div>

  <router-view />

</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from './composables/useTranslation'
import { useUser } from './composables/useUser'

const router = useRouter()
const { t, locale, setLocale } = useTranslation()
const { isLoggedIn, username, isAdmin, fetchUserInfo, logout: logoutUser } = useUser()
const theme = ref("purple")
const showLogoutToast = ref(false)
const accountIconUrl = '/static/general_icons/account_circle.svg#main'
const cancelIconUrl = '/static/general_icons/cancel.svg#main'

// Auto-hide logout toast after 5 seconds
watch(showLogoutToast, (newValue) => {
  if (newValue) {
    setTimeout(() => {
      showLogoutToast.value = false
    }, 5000)
  }
})

function handleLogout() {
  logoutUser()
  showLogoutToast.value = true
  router.push('/')
}

function applyTheme() {
  document.documentElement.setAttribute('data-theme', theme.value)
}

function toggleTheme() {
  const themes = ['purple', 'teal', 'peach', 'orange', 'forest', 'red', 'light', 'dark']
  const currentIndex = themes.indexOf(theme.value)
  const nextIndex = (currentIndex + 1) % themes.length
  theme.value = themes[nextIndex] || 'purple'
  applyTheme()
}

onMounted(() => {
  applyTheme()
  fetchUserInfo()
})
</script>
