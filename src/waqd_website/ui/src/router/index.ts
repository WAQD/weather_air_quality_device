import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import UserHome from '../views/UserHome.vue'
import Login from '../views/Login.vue'
import About from '../views/About.vue'
import Admin from '../views/Admin.vue'
import Account from '../views/Account.vue'
import Devices from '../views/Devices.vue'
import Device from '../views/Device.vue'
import Weather from '../views/Weather.vue'
import ForgotPassword from '../views/ForgotPassword.vue'
import ResetPassword from '../views/ResetPassword.vue'
import { useUser } from '../composables/useUser'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/public/home'
    },
    {
      path: '/public/home',
      name: 'home',
      component: Home
    },
    {
      path: '/home',
      name: 'user-home',
      component: UserHome,
      meta: { requiresAuth: true }
    },
    {
      path: '/public/login',
      name: 'login',
      component: Login
    },
    {
      path: '/public/forgot-password',
      name: 'forgot-password',
      component: ForgotPassword
    },
    {
      path: '/public/reset-password',
      name: 'reset-password',
      component: ResetPassword
    },
    {
      path: '/rest/devices',
      name: 'devices',
      component: Devices,
      meta: { requiresAuth: true }
    },
    {
      path: '/rest/device/:id',
      name: 'device',
      component: Device,
      meta: { requiresAuth: true }
    },
    {
      path: '/rest/weather',
      name: 'weather',
      component: Weather,
      meta: { requiresAuth: true }
    },
    {
      path: '/public/about',
      name: 'about',
      component: About
    },
    {
      path: '/account',
      name: 'account',
      component: Account,
      meta: { requiresAuth: true }
    },
    {
      path: '/admin',
      name: 'admin',
      component: Admin,
      meta: { requiresAuth: true, requiresAdmin: true }
    }
  ],
  // Explicit scroll handling so the browser's native history scroll restoration
  // doesn't reapply a stale scroll position (e.g. left over from a widget deep link).
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

// Navigation guard to protect routes
router.beforeEach(async (to, from, next) => {
  const { isLoggedIn, isAdmin, fetchUserInfo, isLoading, userInfo } = useUser()

  // Fetch user info if not already loaded and not currently loading
  if (!userInfo.value && !isLoading.value) {
    await fetchUserInfo()
  }

  // Wait for loading to complete
  while (isLoading.value) {
    await new Promise(resolve => setTimeout(resolve, 10))
  }

  // Check if route requires authentication
  if (to.meta.requiresAuth && !isLoggedIn.value) {
    next('/public/login')
    return
  }

  // Check if route requires admin
  if (to.meta.requiresAdmin && !isAdmin.value) {
    next('/public/home')
    return
  }

  next()
})

export default router
