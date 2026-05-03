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
})
