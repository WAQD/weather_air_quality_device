import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import i18n, { initI18n } from './i18n'
import { registerSW } from 'virtual:pwa-register'

// Register service worker for PWA
const updateSW = registerSW({
  onNeedRefresh() {
    // Optional: show a prompt to the user
    if (confirm('New content available. Reload?')) {
      updateSW(true)
    }
  },
  onOfflineReady() {
    console.log('App ready to work offline')
  },
})

// Initialize i18n with lazy loading
initI18n().then(() => {
  createApp(App)
    .use(router)
    .use(i18n)
    .mount('#app')
})
