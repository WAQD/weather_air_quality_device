import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import i18n, { loadTranslations, setLocale, getStoredLocale } from './i18n'

// Load translations and initialize app
loadTranslations().then(() => {
  // Set locale from localStorage or default to 'en'
  const storedLocale = getStoredLocale()
  setLocale(storedLocale)
  
  createApp(App)
    .use(router)
    .use(i18n)
    .mount('#app')
})
