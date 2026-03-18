import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import RegisterView from './RegisterView.vue'
import * as authModule from '../api/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: { template: '<div />' } },
    { path: '/register', component: RegisterView },
  ],
})

function mountRegister() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(RegisterView, { global: { plugins: [router, pinia] } })
}

beforeEach(async () => {
  vi.restoreAllMocks()
  await router.push('/register')
})

describe('RegisterView', () => {
  it('renders email and password inputs', () => {
    const wrapper = mountRegister()
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('shows no error initially', () => {
    const wrapper = mountRegister()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('calls authApi.register and redirects to login on success', async () => {
    const registerSpy = vi.spyOn(authModule.authApi, 'register').mockResolvedValue({
      id: 'u1',
      email: 'new@test.com',
      is_active: true,
      created_at: '2024-01-01',
    })

    const wrapper = mountRegister()
    await wrapper.find('input[type="email"]').setValue('new@test.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(registerSpy).toHaveBeenCalledWith('new@test.com', 'password123')
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('displays error message when registration fails', async () => {
    vi.spyOn(authModule.authApi, 'register').mockRejectedValue(new Error('HTTP 409'))

    const wrapper = mountRegister()
    await wrapper.find('input[type="email"]').setValue('existing@test.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Impossible de créer le compte')
  })

  it('sets aria-busy on button while loading', async () => {
    let resolve!: (v: unknown) => void
    vi.spyOn(authModule.authApi, 'register').mockReturnValue(
      new Promise((r) => { resolve = r as (v: unknown) => void }),
    )

    const wrapper = mountRegister()
    await wrapper.find('input[type="email"]').setValue('u@t.com')
    await wrapper.find('input[type="password"]').setValue('password1')
    wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('button[type="submit"]').attributes('aria-busy')).toBe('true')
    resolve({ id: 'u1', email: 'u@t.com', is_active: true, created_at: '' })
    await flushPromises()
    expect(wrapper.find('button[type="submit"]').attributes('aria-busy')).toBe('false')
  })
})
