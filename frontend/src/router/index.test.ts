import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { makeFakeJwt } from '../__tests__/helpers'
import router from './index'

beforeEach(async () => {
  setActivePinia(createPinia())
  await router.push('/')
})

describe('Router guard', () => {
  it('allows access to / without authentication', async () => {
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('allows access to /login without authentication', async () => {
    await router.push('/login')
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('allows access to /register without authentication', async () => {
    await router.push('/register')
    expect(router.currentRoute.value.name).toBe('register')
  })

  it('redirects unauthenticated user to login when accessing /users', async () => {
    await router.push('/users')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/users')
  })

  it('redirects unauthenticated user to login when accessing /roles', async () => {
    await router.push('/roles')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/roles')
  })

  it('redirects unauthenticated user to login when accessing /permissions', async () => {
    await router.push('/permissions')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/permissions')
  })

  it('redirects authenticated user without permission to home', async () => {
    const store = useAuthStore()
    store.setTokens(makeFakeJwt({ permissions: [] }), 'ref')

    await router.push('/users')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('allows authenticated user with users:manage to access /users', async () => {
    const store = useAuthStore()
    store.setTokens(makeFakeJwt({ permissions: ['users:manage'] }), 'ref')

    await router.push('/users')
    expect(router.currentRoute.value.name).toBe('users')
  })

  it('allows authenticated user with users:manage to access /roles', async () => {
    const store = useAuthStore()
    store.setTokens(makeFakeJwt({ permissions: ['users:manage'] }), 'ref')

    await router.push('/roles')
    expect(router.currentRoute.value.name).toBe('roles')
  })

  it('allows authenticated user with users:manage to access /permissions', async () => {
    const store = useAuthStore()
    store.setTokens(makeFakeJwt({ permissions: ['users:manage'] }), 'ref')

    await router.push('/permissions')
    expect(router.currentRoute.value.name).toBe('permissions')
  })
})
