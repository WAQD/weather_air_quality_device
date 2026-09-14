import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import i18n, { initI18n } from './i18n'

// Set __waqdNavigate immediately so Android can call it at any time during cold start,
// even before initI18n finishes. Any path called before the app is ready gets queued
// and flushed once the router is live.
let _pendingNavPath: string | null = null
  ; (window as any).__waqdNavigate = (path: string) => {
    _pendingNavPath = path
  }

// Startup banner so it is obvious which backend the app targets and in which mode it runs.
console.info(
  `[waqd] frontend mode=${import.meta.env.DEV ? 'development' : 'production'} | API base=${__WAQD_BASE_URL__}` +
  (import.meta.env.DEV ? ' (dev: /api and /ws are proxied by the Vite dev server)' : '')
)

initI18n().then(() => {
  createApp(App)
    .use(router)
    .use(i18n)
    .mount('#app')

    // Upgrade to real navigation now that the router is ready
    ; (window as any).__waqdNavigate = (path: string) => router.push(path)

  // Flush any navigation queued before the app was ready (cold-start widget tap)
  if (_pendingNavPath) {
    router.push(_pendingNavPath)
    _pendingNavPath = null
  }
})
