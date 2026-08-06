import { ref, computed } from 'vue'
import { Preferences } from '@capacitor/preferences'

interface UserInfo {
  username: string
  email?: string | null
  permissions: string[]
  widget_key?: string | null
}

const userInfo = ref<UserInfo | null>(null)
const isLoading = ref(false)

export function useUser() {
  const isLoggedIn = computed(() => !!userInfo.value?.username)
  const username = computed(() => userInfo.value?.username ?? '')
  const isAdmin = computed(() => userInfo.value?.permissions?.includes('users:admin') ?? false)

  async function persistWidgetConfig(user: UserInfo): Promise<void> {
    try {
      if (user.widget_key) {
        await Preferences.set({ key: 'waqd.widget.key', value: user.widget_key })
      }
      const baseUrl = window.location.origin.startsWith('http')
        ? window.location.origin
        : __WAQD_BASE_URL__
      await Preferences.set({ key: 'waqd.background.apiBaseUrl', value: baseUrl })
    } catch {
      // non-critical
    }
  }

  async function fetchUserInfo(): Promise<UserInfo | null> {
    isLoading.value = true
    try {
      const response = await fetch('/api/user/me', {
        credentials: 'include',
      })

      if (response.ok) {
        const data = await response.json()
        userInfo.value = data
        await persistWidgetConfig(data)
        return data
      } else {
        userInfo.value = null
        return null
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error)
      userInfo.value = null
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    try {
      await fetch('/api/public/logout', {
        method: 'POST',
        credentials: 'include',
      })
    } catch (error) {
      console.error('Failed to logout:', error)
    } finally {
      userInfo.value = null
      window.dispatchEvent(new CustomEvent('user-logout'))
    }
  }

  return {
    userInfo,
    isLoggedIn,
    username,
    isAdmin,
    isLoading,
    fetchUserInfo,
    logout,
  }
}
