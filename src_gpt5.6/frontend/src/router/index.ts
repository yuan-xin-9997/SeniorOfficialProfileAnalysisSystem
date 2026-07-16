import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    { path: '/dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/officials', component: () => import('@/views/OfficialListView.vue') },
    { path: '/officials/:id', component: () => import('@/views/OfficialDetailView.vue') },
    { path: '/network', component: () => import('@/views/NetworkView.vue') },
    { path: '/admin/scraper', component: () => import('@/views/ScraperAdminView.vue'), meta: { admin: true } },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return '/login'
  if (to.meta.admin && !auth.isAdmin) return '/dashboard'
  return true
})

export default router
