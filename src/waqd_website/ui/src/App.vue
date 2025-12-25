<template>
  <Navbar />
  <div class="bg-gradient-to-b from-base-200 to-base-300 overflow-x-hidden">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import Navbar from './components/Navbar.vue'
import { useUser } from './composables/useUser'

const { fetchUserInfo } = useUser()

onMounted(() => {
  fetchUserInfo()
})
</script>

<style>
/* Global styles can go here */
</style>
