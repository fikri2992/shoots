import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authed = { requiresAuth: true }

const routes = [
  { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue') },
  { path: '/', name: 'now', component: () => import('@/pages/NowPage.vue'), meta: authed },
  { path: '/shots', name: 'shots', component: () => import('@/pages/ShotsPage.vue'), meta: authed },
  {
    path: '/shots/:shotId',
    name: 'shot',
    component: () => import('@/pages/ShotPage.vue'),
    props: true,
    meta: authed,
  },
  { path: '/journey', name: 'journey', component: () => import('@/pages/JourneyPage.vue'), meta: authed },

  { path: '/frames', redirect: { name: 'shots' } },
  { path: '/frames/:shotId', redirect: (to) => ({ name: 'shot', params: to.params }) },
  { path: '/map', redirect: { name: 'journey' } },
  { path: '/feed', redirect: { name: 'journey' } },
  { path: '/:pathMatch(.*)*', redirect: { name: 'now' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved || { top: 0 },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.resolved) await auth.fetchMe()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return { name: 'login' }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'now' }
  return true
})

export default router
