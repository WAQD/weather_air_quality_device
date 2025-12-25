import { ref, computed } from 'vue'

interface UserInfo {
  username: string
  permissions: string[]
}

const userInfo = ref<UserInfo | null>(null)
const isLoading = ref(false)

export function useUser() {
  const isLoggedIn = computed(() => !!userInfo.value?.username)
  const username = computed(() => userInfo.value?.username ?? '')
  const isAdmin = computed(() => userInfo.value?.permissions?.includes('users:admin') ?? false)

  async function fetchUserInfo() {
    isLoading.value = true
    try {
      const response = await fetch('/api/user/me', {
        credentials: 'include',
      })
      
      if (response.ok) {
        userInfo.value = await response.json()
      } else {
        userInfo.value = null
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error)
      userInfo.value = null
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
