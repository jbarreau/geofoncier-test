import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'

function makeToken(payload: {
  sub?: string
  email?: string
  roles?: string[]
  permissions?: string[]
  exp?: number
}): string {
  const header = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' }))
  const body = btoa(
    JSON.stringify({
      sub: payload.sub ?? 'user-id',
      email: payload.email ?? 'test@example.com',
      roles: payload.roles ?? [],
      permissions: payload.permissions ?? [],
      exp: payload.exp ?? 9999999999,
    }),
  )
  return `${header}.${body}.fakesignature`
}

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('setTokens extracts permissions and roles from JWT', () => {
    const store = useAuthStore()
    const token = makeToken({ roles: ['admin'], permissions: ['tasks:create', 'tasks:delete'] })

    store.setTokens(token, 'refresh-token')

    expect(store.permissions).toEqual(['tasks:create', 'tasks:delete'])
    expect(store.roles).toEqual(['admin'])
    expect(store.email).toBe('test@example.com')
    expect(store.isAuthenticated).toBe(true)
  })

  it('setTokens persists tokens to localStorage', () => {
    const store = useAuthStore()
    const token = makeToken({})

    store.setTokens(token, 'my-refresh')

    expect(localStorage.getItem('access_token')).toBe(token)
    expect(localStorage.getItem('refresh_token')).toBe('my-refresh')
  })

  it('hasPermission returns true for granted permission', () => {
    const store = useAuthStore()
    store.setTokens(makeToken({ permissions: ['tasks:read', 'tasks:create'] }), 'r')

    expect(store.hasPermission('tasks:read')).toBe(true)
    expect(store.hasPermission('tasks:create')).toBe(true)
  })

  it('hasPermission returns false for missing permission', () => {
    const store = useAuthStore()
    store.setTokens(makeToken({ permissions: ['tasks:read'] }), 'r')

    expect(store.hasPermission('tasks:delete')).toBe(false)
    expect(store.hasPermission('users:manage')).toBe(false)
  })

  it('hasRole returns true for assigned role', () => {
    const store = useAuthStore()
    store.setTokens(makeToken({ roles: ['admin'] }), 'r')

    expect(store.hasRole('admin')).toBe(true)
  })

  it('hasRole returns false for unassigned role', () => {
    const store = useAuthStore()
    store.setTokens(makeToken({ roles: ['user'] }), 'r')

    expect(store.hasRole('admin')).toBe(false)
    expect(store.hasRole('viewer')).toBe(false)
  })

  it('clearTokens resets all state', () => {
    const store = useAuthStore()
    store.setTokens(
      makeToken({ roles: ['admin'], permissions: ['tasks:create'] }),
      'refresh',
    )

    store.clearTokens()

    expect(store.accessToken).toBeNull()
    expect(store.refreshToken).toBeNull()
    expect(store.permissions).toEqual([])
    expect(store.roles).toEqual([])
    expect(store.email).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('starts unauthenticated when localStorage is empty', () => {
    const store = useAuthStore()

    expect(store.isAuthenticated).toBe(false)
    expect(store.permissions).toEqual([])
    expect(store.roles).toEqual([])
  })
})
