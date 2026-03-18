import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './HomeView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/login', component: { template: '<div />' } },
    { path: '/users', component: { template: '<div />' } },
    { path: '/roles', component: { template: '<div />' } },
    { path: '/permissions', component: { template: '<div />' } },
    { path: '/tasks', component: { template: '<div />' } },
  ],
})

function mountHome(storeSetup: (store: ReturnType<typeof useAuthStore>) => void = () => {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useAuthStore()
  storeSetup(store)
  return mount(HomeView, { global: { plugins: [router, pinia] } })
}

beforeEach(async () => {
  await router.push('/')
})

describe('HomeView', () => {
  it('shows login prompt when not authenticated', () => {
    const wrapper = mountHome()
    expect(wrapper.find('.not-authenticated').exists()).toBe(true)
    expect(wrapper.text()).toContain('Connexion requise')
  })

  it('shows welcome message when authenticated', () => {
    const wrapper = mountHome((store) => {
      store.accessToken = 'tok'
      store.email = 'admin@example.com'
    })
    expect(wrapper.text()).toContain('Bienvenue')
    expect(wrapper.text()).toContain('admin@example.com')
    expect(wrapper.find('.not-authenticated').exists()).toBe(false)
  })

  it('shows "Accès limité" when authenticated with no relevant permissions', () => {
    const wrapper = mountHome((store) => {
      store.accessToken = 'tok'
      store.email = 'user@test.com'
      store.permissions = []
    })
    expect(wrapper.find('.grid').exists()).toBe(false)
    expect(wrapper.text()).toContain('Accès limité')
  })

  it('shows tasks card grid when user has tasks:read', () => {
    const wrapper = mountHome((store) => {
      store.accessToken = 'tok'
      store.permissions = ['tasks:read']
    })
    expect(wrapper.find('.grid').exists()).toBe(true)
    expect(wrapper.text()).toContain('Tâches')
  })

  it('shows admin cards grid when user has users:manage', () => {
    const wrapper = mountHome((store) => {
      store.accessToken = 'tok'
      store.permissions = ['users:manage']
    })
    expect(wrapper.find('.grid').exists()).toBe(true)
    expect(wrapper.text()).toContain('Utilisateurs')
    expect(wrapper.text()).toContain('Rôles')
    expect(wrapper.text()).toContain('Permissions')
  })

  it('shows all cards when user has both tasks:read and users:manage', () => {
    const wrapper = mountHome((store) => {
      store.accessToken = 'tok'
      store.permissions = ['tasks:read', 'users:manage']
    })
    expect(wrapper.find('.grid').exists()).toBe(true)
    expect(wrapper.text()).toContain('Tâches')
    expect(wrapper.text()).toContain('Utilisateurs')
  })
})
