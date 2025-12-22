<template>
  <div class="container mx-auto p-8">
    <h1 class="text-4xl font-bold mb-8">{{ t('admin_controls') }}</h1>
    
    <div v-if="loading" class="flex justify-center items-center min-h-[50vh]">
      <span class="loading loading-spinner loading-lg"></span>
    </div>
    
    <div v-else-if="error" class="alert alert-error">
      <span>{{ error }}</span>
    </div>
    
    <div v-else class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title text-2xl mb-4">{{ t('users') }}</h2>
        
        <div class="overflow-x-auto">
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>{{ t('username') }}</th>
                <th>{{ t('permissions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.username">
                <td class="font-semibold">{{ user.username }}</td>
                <td>
                  <div class="flex gap-2 flex-wrap">
                    <span
                      v-for="permission in user.permissions"
                      :key="permission"
                      class="badge badge-primary"
                    >
                      {{ permission }}
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslation } from '../composables/useTranslation'

const router = useRouter()
const { t } = useTranslation()

interface User {
  username: string
  permissions: string[]
}

const users = ref<User[]>([])
const loading = ref(true)
const error = ref('')

async function fetchUsers() {
  loading.value = true
  error.value = ''
  
  try {
    const response = await fetch('/api/user/admin/users', {
      credentials: 'include',
    })
    
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        error.value = t('admin_access_denied')
        setTimeout(() => router.push('/'), 2000)
      } else {
        error.value = t('failed_to_load_users')
      }
      return
    }
    
    users.value = await response.json()
  } catch (err) {
    console.error('Failed to fetch users:', err)
    error.value = t('failed_to_load_users')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
