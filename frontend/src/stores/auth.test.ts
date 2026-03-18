import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'
import { makeFakeJwt } from '../__tests__/helpers'

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('useAuthStore — initial state', () => {
  it('is not authenticated when localStorage is empty', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.accessToken).toBeNull()
    expect(store.permissions).toEqual([])
    expect(store.email).toBeNull()
  })

  it('rehydrates from localStorage on init', () => {
    const jwt = makeFakeJwt({ email: 'admin@example.com', permissions: ['users:manage'] })
    localStorage.setItem('access_token', jwt)
    localStorage.setItem('refresh_token', 'ref')

    // Create a fresh store after setting localStorage
    setActivePinia(createPinia())
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(true)
    expect(store.email).toBe('admin@example.com')
    expect(store.permissions).toContain('users:manage')
  })

  it('clears tokens when stored JWT is invalid', () => {
    localStorage.setItem('access_token', 'not.a.jwt')
    localStorage.setItem('refresh_token', 'ref')

    setActivePinia(createPinia())
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.accessToken).toBeNull()
  })
})

describe('useAuthStore.setTokens', () => {
  it('stores tokens and decodes JWT payload', () => {
    const store = useAuthStore()
    const jwt = makeFakeJwt({ email: 'user@test.com', permissions: ['tasks:read', 'tasks:write'] })
    store.setTokens(jwt, 'my-refresh-token')

    expect(store.accessToken).toBe(jwt)
    expect(store.refreshToken).toBe('my-refresh-token')
    expect(store.email).toBe('user@test.com')
    expect(store.permissions).toEqual(['tasks:read', 'tasks:write'])
    expect(store.isAuthenticated).toBe(true)
  })

  it('persists tokens in localStorage', () => {
    const store = useAuthStore()
    const jwt = makeFakeJwt()
    store.setTokens(jwt, 'ref')

    expect(localStorage.setItem).toHaveBeenCalledWith('access_token', jwt)
    expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'ref')
  })
})

describe('useAuthStore.clearTokens', () => {
  it('clears all state', () => {
    const store = useAuthStore()
    const jwt = makeFakeJwt({ email: 'user@test.com' })
    store.setTokens(jwt, 'ref')

    store.clearTokens()
    expect(store.accessToken).toBeNull()
    expect(store.refreshToken).toBeNull()
    expect(store.permissions).toEqual([])
    expect(store.email).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('removes tokens from localStorage', () => {
    const store = useAuthStore()
    store.setTokens(makeFakeJwt(), 'ref')
    store.clearTokens()

    expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
    expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
  })
})

describe('useAuthStore.hasPermission', () => {
  it('returns true when permission is present', () => {
    const store = useAuthStore()
    store.setTokens(makeFakeJwt({ permissions: ['users:manage', 'tasks:read'] }), 'ref')
    expect(store.hasPermission('users:manage')).toBe(true)
    expect(store.hasPermission('tasks:read')).toBe(true)
  })

  it('returns false when permission is absent', () => {
    const store = useAuthStore()
    store.setTokens(makeFakeJwt({ permissions: ['tasks:read'] }), 'ref')
    expect(store.hasPermission('users:manage')).toBe(false)
  })

  it('returns false when not authenticated', () => {
    const store = useAuthStore()
    expect(store.hasPermission('users:manage')).toBe(false)
  })
})
