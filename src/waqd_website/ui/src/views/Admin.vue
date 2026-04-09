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
        <div class="flex justify-between items-center mb-4">
          <h2 class="card-title text-2xl">{{ t('users') }}</h2>
          <button class="btn btn-primary" @click="openAddUserModal">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6zM16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z" />
            </svg>
            {{ t('add_user') }}
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="table table-zebra">
            <thead>
              <tr>
                <th>{{ t('username') }}</th>
                <th>{{ t('email') }}</th>
                <th>{{ t('permissions') }}</th>
                <th class="text-right">{{ t('actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.username">
                <td class="font-semibold">{{ user.username }}</td>
                <td class="text-sm opacity-70">{{ user.email ?? '—' }}</td>
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
                <td class="text-right">
                  <div class="flex gap-2 justify-end">
                    <button 
                      class="btn btn-sm btn-info"
                      @click="openPasswordModal(user.username)"
                      :title="t('change_password')"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
                      </svg>
                    </button>
                    <button 
                      class="btn btn-sm btn-error"
                      @click="openDeleteModal(user.username)"
                      :title="t('delete_user')"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Add User Modal -->
    <dialog ref="addUserModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">{{ t('add_user') }}</h3>
        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">{{ t('username') }}</span>
          </label>
          <input
            v-model="newUser.username"
            type="text"
            class="input input-bordered w-full"
            :placeholder="t('enter_username')"
          />
        </div>
        <div class="form-control w-full mb-4">
          <label class="label">
            <span class="label-text">{{ t('permissions') }}</span>
          </label>
          <div class="flex gap-2 flex-wrap">
            <label class="cursor-pointer label gap-2">
              <input
                type="checkbox"
                class="checkbox checkbox-primary"
                value="users:admin"
                v-model="newUser.permissions"
              />
              <span class="label-text">users:admin</span>
            </label>
          </div>
        </div>
        <div v-if="addUserError" class="alert alert-error mb-4">
          <span>{{ addUserError }}</span>
        </div>
        <div class="modal-action">
          <button class="btn" @click="closeAddUserModal">{{ t('cancel') }}</button>
          <button class="btn btn-primary" @click="addUser" :disabled="!newUser.username">
            {{ t('add') }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>

    <!-- Change Password Modal -->
    <dialog ref="passwordModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">{{ t('change_password') }}</h3>
        <p class="mb-4">{{ t('changing_password_for') }}: <strong>{{ selectedUsername }}</strong></p>
        <div class="form-control w-full mb-4">
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
        <div class="form-control w-full mb-4">
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
        <div v-if="passwordError" class="alert alert-error mb-4">
          <span>{{ passwordError }}</span>
        </div>
        <div class="modal-action">
          <button class="btn" @click="closePasswordModal">{{ t('cancel') }}</button>
          <button 
            class="btn btn-primary" 
            @click="changePassword"
            :disabled="!newPassword || !confirmPassword"
          >
            {{ t('change_password') }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>

    <!-- Delete User Modal -->
    <dialog ref="deleteModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">{{ t('delete_user') }}</h3>
        <p class="mb-4">{{ t('confirm_delete_user') }}: <strong>{{ selectedUsername }}</strong>?</p>
        <div v-if="deleteError" class="alert alert-error mb-4">
          <span>{{ deleteError }}</span>
        </div>
        <div class="modal-action">
          <button class="btn" @click="closeDeleteModal">{{ t('cancel') }}</button>
          <button class="btn btn-error" @click="deleteUser">{{ t('delete') }}</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
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
  email?: string
  permissions: string[]
}

const users = ref<User[]>([])
const loading = ref(true)
const error = ref('')

// Add User Modal
const addUserModal = ref<HTMLDialogElement | null>(null)
const newUser = ref({
  username: '',
  permissions: [] as string[]
})
const addUserError = ref('')

// Password Modal
const passwordModal = ref<HTMLDialogElement | null>(null)
const selectedUsername = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')

// Delete Modal
const deleteModal = ref<HTMLDialogElement | null>(null)
const deleteError = ref('')

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

// Add User Functions
function openAddUserModal() {
  newUser.value = { username: '', permissions: [] }
  addUserError.value = ''
  addUserModal.value?.showModal()
}

function closeAddUserModal() {
  addUserModal.value?.close()
}

async function addUser() {
  addUserError.value = ''
  
  if (!newUser.value.username) {
    addUserError.value = t('username_required')
    return
  }

  try {
    const response = await fetch('/api/user/admin/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        username: newUser.value.username,
        permissions: newUser.value.permissions
      }),
    })

    if (!response.ok) {
      const errorData = await response.json()
      addUserError.value = errorData.detail || t('failed_to_add_user')
      return
    }

    await fetchUsers()
    closeAddUserModal()
  } catch (err) {
    console.error('Failed to add user:', err)
    addUserError.value = t('failed_to_add_user')
  }
}

// Password Functions
function openPasswordModal(username: string) {
  selectedUsername.value = username
  newPassword.value = ''
  confirmPassword.value = ''
  passwordError.value = ''
  passwordModal.value?.showModal()
}

function closePasswordModal() {
  passwordModal.value?.close()
}

async function changePassword() {
  passwordError.value = ''

  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = t('passwords_do_not_match')
    return
  }

  if (newPassword.value.length < 6) {
    passwordError.value = t('password_too_short')
    return
  }

  try {
    const response = await fetch(`/api/user/users/${selectedUsername.value}/password`, {
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

    closePasswordModal()
  } catch (err) {
    console.error('Failed to change password:', err)
    passwordError.value = t('failed_to_change_password')
  }
}

// Delete Functions
function openDeleteModal(username: string) {
  selectedUsername.value = username
  deleteError.value = ''
  deleteModal.value?.showModal()
}

function closeDeleteModal() {
  deleteModal.value?.close()
}

async function deleteUser() {
  deleteError.value = ''

  try {
    const response = await fetch(`/api/user/admin/users/${selectedUsername.value}`, {
      method: 'DELETE',
      credentials: 'include',
    })

    if (!response.ok) {
      const errorData = await response.json()
      deleteError.value = errorData.detail || t('failed_to_delete_user')
      return
    }

    await fetchUsers()
    closeDeleteModal()
  } catch (err) {
    console.error('Failed to delete user:', err)
    deleteError.value = t('failed_to_delete_user')
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
