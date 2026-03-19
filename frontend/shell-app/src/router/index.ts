import { createRouter, createWebHistory } from 'vue-router'
import { defineAsyncComponent } from 'vue'
import { useAuthStore } from '../stores/auth'
import HomeView from '../views/HomeView.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import RemoteError from '../components/RemoteError.vue'

const asyncOpts = {
  loadingComponent: LoadingSpinner,
  errorComponent: RemoteError,
  delay: 200,
  timeout: 10000,
}

const RemoteLoginView = defineAsyncComponent({
  ...asyncOpts,
  loader: () => import('auth-front/LoginView'),
})

const RemoteRegisterView = defineAsyncComponent({
  ...asyncOpts,
  loader: () => import('auth-front/RegisterView'),
})

const RemoteUsersView = defineAsyncComponent({
  ...asyncOpts,
  loader: () => import('auth-front/UsersView'),
})

const RemoteRolesView = defineAsyncComponent({
  ...asyncOpts,
  loader: () => import('auth-front/RolesView'),
})

const RemotePermissionsView = defineAsyncComponent({
  ...asyncOpts,
  loader: () => import('auth-front/PermissionsView'),
})

const RemoteTaskList = defineAsyncComponent({
  ...asyncOpts,
  loader: () => import('task-front/TaskList'),
})

const RemoteDashboard = defineAsyncComponent({
  ...asyncOpts,
  loader: () => import('analytics-front/Dashboard'),
})

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
      component: RemoteLoginView,
    },
    {
      path: '/register',
      name: 'register',
      component: RemoteRegisterView,
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: RemoteTaskList,
      meta: { requiresPermission: 'tasks:read' },
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: RemoteDashboard,
      meta: { requiresPermission: 'analytics:read' },
    },
    {
      path: '/users',
      name: 'users',
      component: RemoteUsersView,
      meta: { requiresPermission: 'users:manage' },
    },
    {
      path: '/roles',
      name: 'roles',
      component: RemoteRolesView,
      meta: { requiresPermission: 'users:manage' },
    },
    {
      path: '/permissions',
      name: 'permissions',
      component: RemotePermissionsView,
      meta: { requiresPermission: 'users:manage' },
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
