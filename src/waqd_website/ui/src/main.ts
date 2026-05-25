import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import i18n, { initI18n } from './i18n'

// Initialize i18n with lazy loading
initI18n().then(() => {
  createApp(App)
    .use(router)
    .use(i18n)
    .mount('#app')

  // Expose router for direct native navigation (Android widget tap).
  // Called immediately if app is already running, otherwise sessionStorage
  // fallback is checked in App.vue onMounted.
  ;(window as any).__waqdNavigate = (path: string) => router.push(path)
})
