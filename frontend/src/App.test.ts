import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import { useAuthStore } from './stores/auth'
import * as authModule from './api/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/login', component: { template: '<div />' } },
    { path: '/users', component: { template: '<div />' } },
    { path: '/roles', component: { template: '<div />' } },
    { path: '/permissions', component: { template: '<div />' } },
    { path: '/tasks', component: { template: '<div />' } },
    { path: '/analytics', component: { template: '<div />' } },
  ],
})

function mountApp(storeSetup: (store: ReturnType<typeof useAuthStore>) => void = () => {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useAuthStore()
  storeSetup(store)
  return mount(App, { global: { plugins: [router, pinia] } })
}

beforeEach(async () => {
  vi.restoreAllMocks()
  await router.push('/')
})

describe('App.vue — navigation bar', () => {
  it('shows Connexion link when not authenticated', () => {
    const wrapper = mountApp()
    expect(wrapper.text()).toContain('Connexion')
    expect(wrapper.text()).not.toContain('Déconnexion')
  })

  it('does not show admin links when not authenticated', () => {
    const wrapper = mountApp()
    expect(wrapper.text()).not.toContain('Utilisateurs')
    expect(wrapper.text()).not.toContain('Rôles')
    expect(wrapper.text()).not.toContain('Permissions')
  })

  it('shows Déconnexion button when authenticated', () => {
    const wrapper = mountApp((store) => {
      store.accessToken = 'tok'
      store.email = 'user@test.com'
    })
    expect(wrapper.text()).toContain('Déconnexion')
    expect(wrapper.text()).not.toContain('Connexion')
  })

  it('shows email when authenticated', () => {
    const wrapper = mountApp((store) => {
      store.accessToken = 'tok'
      store.email = 'admin@test.com'
    })
    expect(wrapper.text()).toContain('admin@test.com')
  })

  it('shows admin links when user has users:manage permission', () => {
    const wrapper = mountApp((store) => {
      store.accessToken = 'tok'
      store.permissions = ['users:manage']
    })
    expect(wrapper.text()).toContain('Utilisateurs')
    expect(wrapper.text()).toContain('Rôles')
    expect(wrapper.text()).toContain('Permissions')
  })

  it('does not show admin links when authenticated without users:manage', () => {
    const wrapper = mountApp((store) => {
      store.accessToken = 'tok'
      store.permissions = ['tasks:read']
    })
    expect(wrapper.text()).not.toContain('Utilisateurs')
    expect(wrapper.text()).not.toContain('Rôles')
    expect(wrapper.text()).not.toContain('Permissions')
  })

  it('shows Analytics link when user has analytics:read', () => {
    const wrapper = mountApp((store) => {
      store.accessToken = 'tok'
      store.permissions = ['analytics:read']
    })
    expect(wrapper.text()).toContain('Analytics')
  })

  it('does not show Analytics link when user lacks analytics:read', () => {
    const wrapper = mountApp((store) => {
      store.accessToken = 'tok'
      store.permissions = ['tasks:read']
    })
    expect(wrapper.text()).not.toContain('Analytics')
  })

  it('does not show Analytics link when not authenticated', () => {
    const wrapper = mountApp()
    expect(wrapper.text()).not.toContain('Analytics')
  })
})

describe('App.vue — logout', () => {
  it('calls authApi.logout then clears tokens and redirects to /login', async () => {
    const logoutSpy = vi.spyOn(authModule.authApi, 'logout').mockResolvedValue(undefined)

    const wrapper = mountApp((store) => {
      store.accessToken = 'acc'
      store.refreshToken = 'ref'
      store.email = 'u@test.com'
    })

    const btn = wrapper.find('button.secondary')
    await btn.trigger('click')
    await flushPromises()

    expect(logoutSpy).toHaveBeenCalledWith('acc', 'ref')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('still redirects to /login even if authApi.logout throws', async () => {
    vi.spyOn(authModule.authApi, 'logout').mockRejectedValue(new Error('Network'))

    const wrapper = mountApp((store) => {
      store.accessToken = 'acc'
      store.refreshToken = 'ref'
    })

    const btn = wrapper.find('button.secondary')
    await btn.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/login')
  })
})
