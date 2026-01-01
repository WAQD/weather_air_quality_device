<template>
  <div class="container mx-auto p-8">
    <h1 class="text-4xl font-bold mb-8">{{ t('account_settings') }}</h1>
    
    <div v-if="loading" class="flex justify-center items-center min-h-[50vh]">
      <span class="loading loading-spinner loading-lg"></span>
    </div>
    
    <div v-else-if="error" class="alert alert-error">
      <span>{{ error }}</span>
    </div>
    
    <div v-else class="space-y-6">
      <!-- Profile Information Card -->
      <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <h2 class="card-title text-2xl mb-4">{{ t('profile_information') }}</h2>
          
          <div class="form-control w-full max-w-md mb-4">
            <label class="label">
              <span class="label-text">{{ t('username') }}</span>
            </label>
            <input
              v-model="username"
              type="text"
              class="input input-bordered w-full"
              :placeholder="t('enter_username')"
            />
          </div>

          <div class="form-control w-full max-w-md mb-4">
            <label class="label">
              <span class="label-text">{{ t('email') }}</span>
            </label>
            <input
              v-model="email"
              type="email"
              class="input input-bordered w-full"
              :placeholder="t('enter_email')"
            />
          </div>

          <div v-if="updateEmailError" class="alert alert-error mb-4 max-w-md">
            <span>{{ updateEmailError }}</span>
          </div>

          <div v-if="updateEmailSuccess" class="alert alert-success mb-4 max-w-md">
            <span>{{ t('profile_updated_successfully') }}</span>
          </div>

          <div class="card-actions">
            <button 
              class="btn btn-primary"
              @click="updateProfile"
              :disabled="!profileChanged"
            >
              {{ t('update_profile') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Change Password Card -->
      <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <h2 class="card-title text-2xl mb-4">{{ t('change_password') }}</h2>
          
          <div class="form-control w-full max-w-md mb-4">
            <label class="label">
              <span class="label-text">{{ t('new_password') }}</span>
            </label>
            <input
              v-model="newPassword"
              type="password"
              class="input input-bordered w-full"
              :placeholder="t('enter_new_password')"
            />
          </div>

          <div class="form-control w-full max-w-md mb-4">
            <label class="label">
              <span class="label-text">{{ t('confirm_password') }}</span>
            </label>
            <input
              v-model="confirmPassword"
              type="password"
              class="input input-bordered w-full"
              :placeholder="t('confirm_new_password')"
            />
          </div>

          <div v-if="passwordError" class="alert alert-error mb-4 max-w-md">
            <span>{{ passwordError }}</span>
          </div>

          <div v-if="passwordSuccess" class="alert alert-success mb-4 max-w-md">
            <span>{{ t('password_changed_successfully') }}</span>
          </div>

          <div class="card-actions">
            <button 
              class="btn btn-primary"
              @click="changePassword"
              :disabled="!newPassword || !confirmPassword"
            >
              {{ t('change_password') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'
import { useUser } from '../composables/useUser'

const router = useRouter()
const { t } = useTranslation()
const { username: currentUsername, userInfo: currentUserInfo } = useUser()

interface UserInfo {
  username: string
  email?: string
  permissions: string[]
}

const userInfo = ref<UserInfo | null>(null)
const loading = ref(true)
const error = ref('')

// Profile update
const username = ref('')
const originalUsername = ref('')
const email = ref('')
const originalEmail = ref('')
const updateEmailError = ref('')
const updateEmailSuccess = ref(false)

// Password change
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref(false)

const profileChanged = computed(() => {
  return username.value !== originalUsername.value || email.value !== originalEmail.value
})

async function fetchUserInfo() {
  loading.value = true
  error.value = ''
  
  try {
    const response = await fetch('/api/user/me', {
      credentials: 'include',
    })
    
    if (!response.ok) {
      if (response.status === 401) {
        error.value = t('please_login')
        setTimeout(() => router.push('/public/login'), 2000)
      } else {
        error.value = t('failed_to_load_account')
      }
      return
    }
    
    const data = await response.json()
    userInfo.value = data
    username.value = data.username || ''
    originalUsername.value = data.username || ''
    email.value = data.email || ''
    originalEmail.value = data.email || ''
  } catch (err) {
    console.error('Failed to fetch user info:', err)
    error.value = t('failed_to_load_account')
  } finally {
    loading.value = false
  }
}

async function updateProfile() {
  updateEmailError.value = ''
  updateEmailSuccess.value = false

  if (!userInfo.value) return

  try {
    // Update username if changed
    if (username.value !== originalUsername.value) {
      const usernameResponse = await fetch(`/api/user/users/${userInfo.value.username}/username`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          new_username: username.value
        }),
      })

      if (!usernameResponse.ok) {
        const errorData = await usernameResponse.json()
        updateEmailError.value = errorData.detail || t('failed_to_update_username')
        return
      }

      // Username changed, need to update stored values and potentially re-login
      originalUsername.value = username.value
      userInfo.value.username = username.value
    }

    // Update email if changed
    if (email.value !== originalEmail.value) {
      const response = await fetch(`/api/user/users/${userInfo.value.username}/email`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email: email.value || null
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        updateEmailError.value = errorData.detail || t('failed_to_update_email')
        return
      }

      originalEmail.value = email.value
    }

    updateEmailSuccess.value = true

    // Hide success message after 5 seconds
    setTimeout(() => {
      updateEmailSuccess.value = false
    }, 5000)
  } catch (err) {
    console.error('Failed to update profile:', err)
    updateEmailError.value = t('failed_to_update_profile')
  }
}

async function changePassword() {
  passwordError.value = ''
  passwordSuccess.value = false

  if (!userInfo.value) return

  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = t('passwords_do_not_match')
    return
  }

  if (newPassword.value.length < 6) {
    passwordError.value = t('password_too_short')
    return
  }

  try {
    const response = await fetch(`/api/user/users/${userInfo.value.username}/password`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        new_password: newPassword.value
      }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      passwordError.value = errorData.detail || t('failed_to_change_password')
      return
    }

    passwordSuccess.value = true
    newPassword.value = ''
    confirmPassword.value = ''

    // Hide success message after 5 seconds
    setTimeout(() => {
      passwordSuccess.value = false
    }, 5000)
  } catch (err) {
    console.error('Failed to change password:', err)
    passwordError.value = t('failed_to_change_password')
  }
}

onMounted(() => {
  fetchUserInfo()
})
</script>
