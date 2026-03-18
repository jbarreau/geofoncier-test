import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './LoginView.vue'
import * as authModule from '../api/auth'
import { makeFakeJwt } from '../__tests__/helpers'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/login', component: LoginView },
    { path: '/register', component: { template: '<div />' } },
    { path: '/dashboard', component: { template: '<div />' } },
  ],
})

function mountLogin() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(LoginView, { global: { plugins: [router, pinia] } })
}

beforeEach(async () => {
  vi.restoreAllMocks()
  await router.push('/login')
})

describe('LoginView', () => {
  it('renders email and password inputs', () => {
    const wrapper = mountLogin()
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('shows no error initially', () => {
    const wrapper = mountLogin()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('calls authApi.login on submit and redirects to home', async () => {
    const loginSpy = vi.spyOn(authModule.authApi, 'login').mockResolvedValue({
      access_token: makeFakeJwt(),
      refresh_token: 'ref',
      token_type: 'bearer',
    })

    const wrapper = mountLogin()
    await wrapper.find('input[type="email"]').setValue('user@test.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(loginSpy).toHaveBeenCalledWith('user@test.com', 'password123')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('displays error message on failed login', async () => {
    vi.spyOn(authModule.authApi, 'login').mockRejectedValue(new Error('HTTP 401'))

    const wrapper = mountLogin()
    await wrapper.find('input[type="email"]').setValue('bad@test.com')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Identifiants invalides')
  })

  it('sets aria-busy on button while loading', async () => {
    let resolve!: (v: unknown) => void
    vi.spyOn(authModule.authApi, 'login').mockReturnValue(
      new Promise((r) => { resolve = r as (v: unknown) => void }),
    )

    const wrapper = mountLogin()
    await wrapper.find('input[type="email"]').setValue('u@t.com')
    await wrapper.find('input[type="password"]').setValue('pass')
    wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()

    const btn = wrapper.find('button[type="submit"]')
    expect(btn.attributes('aria-busy')).toBe('true')

    resolve({ access_token: makeFakeJwt(), refresh_token: 'r', token_type: 'bearer' })
    await flushPromises()
    expect(btn.attributes('aria-busy')).toBe('false')
  })
})
