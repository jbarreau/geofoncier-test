import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
    },
    {
      path: '/permissions',
      name: 'permissions',
      component: () => import('../views/PermissionsView.vue'),
      meta: { requiresPermission: 'users:manage' },
    },
    {
      path: '/roles',
      name: 'roles',
      component: () => import('../views/RolesView.vue'),
      meta: { requiresPermission: 'users:manage' },
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('../views/UsersView.vue'),
      meta: { requiresPermission: 'users:manage' },
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: () => import('../views/AnalyticsView.vue'),
      meta: { requiresPermission: 'analytics:read' },
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const required = to.meta.requiresPermission as string | undefined

  if (required) {
    if (!auth.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (!auth.hasPermission(required)) {
      return { name: 'home' }
    }
  }
})

export default router
