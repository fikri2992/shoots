import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue') },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/pages/DashboardPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'dashboard' },
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.resolved) await auth.fetchMe()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return { name: 'login' }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'dashboard' }
  return true
})

export default router
