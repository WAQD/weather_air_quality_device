import { onMounted, onUnmounted, ref } from 'vue'

const REFRESH_INTERVAL = 60 * 60 * 1000 // 1 hour in milliseconds
const isRefreshing = ref(false)

export function useTokenRefresh() {
  let intervalId: number | null = null
  let isTabVisible = true

  async function refreshToken() {
    if (isRefreshing.value) {
      return
    }

    isRefreshing.value = true
    try {
      const response = await fetch('/api/public/keepalive', {
        method: 'GET',
        credentials: 'include',
      })

      if (!response.ok) {
        console.error('Token refresh failed:', response.status)
        // Don't logout on error - could be temporary network issue
        // Let the token expire naturally and user will be logged out on next API call
      }
    } catch (error) {
      console.error('Token refresh error:', error)
      // Silent failure - network issues shouldn't force logout
    } finally {
      isRefreshing.value = false
    }
  }

  function startRefreshTimer() {
    if (intervalId !== null) {
      return // Already running
    }

    intervalId = window.setInterval(() => {
      if (isTabVisible) {
        refreshToken()
      }
    }, REFRESH_INTERVAL)

    // Also refresh immediately when starting
    refreshToken()
  }

  function stopRefreshTimer() {
    if (intervalId !== null) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  function handleVisibilityChange() {
    isTabVisible = !document.hidden

    if (isTabVisible) {
      // Tab became visible - refresh token immediately
      refreshToken()
    }
  }

  onMounted(() => {
    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    // Listen for logout events to stop refresh timer
    window.addEventListener('user-logout', stopRefreshTimer)
    
    // Start the refresh timer
    startRefreshTimer()
  })

  onUnmounted(() => {
    // Cleanup
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('user-logout', stopRefreshTimer)
    stopRefreshTimer()
  })

  return {
    refreshToken,
    stopRefreshTimer,
  }
}
