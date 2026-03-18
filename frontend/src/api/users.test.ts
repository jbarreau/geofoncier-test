import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usersApi } from './users'
import { useAuthStore } from '../stores/auth'
import { makeFakeJwt } from '../__tests__/helpers'

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('usersApi — authenticated requests', () => {
  it('list() sends Authorization header', async () => {
    const fetchMock = mockFetch(200, [])
    vi.stubGlobal('fetch', fetchMock)
    const store = useAuthStore()
    store.setTokens(makeFakeJwt(), 'refresh')

    await usersApi.list()
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers['Authorization']).toBe(`Bearer ${store.accessToken}`)
  })

  it('list() works without token (no Authorization header)', async () => {
    const fetchMock = mockFetch(200, [])
    vi.stubGlobal('fetch', fetchMock)

    await usersApi.list()
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers['Authorization']).toBeUndefined()
  })

  it('get() fetches a single user by id', async () => {
    const user = { id: 'u1', email: 'a@b.com', is_active: true, created_at: '', roles: [] }
    const fetchMock = mockFetch(200, user)
    vi.stubGlobal('fetch', fetchMock)

    const result = await usersApi.get('u1')
    expect(result).toEqual(user)
    expect(fetchMock).toHaveBeenCalledWith('/api/users/u1', expect.any(Object))
  })

  it('update() sends PUT with body', async () => {
    const updated = { id: 'u1', email: 'a@b.com', is_active: false, created_at: '', roles: [] }
    const fetchMock = mockFetch(200, updated)
    vi.stubGlobal('fetch', fetchMock)

    const result = await usersApi.update('u1', { is_active: false })
    expect(result).toEqual(updated)
    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('PUT')
    expect(options.body).toBe(JSON.stringify({ is_active: false }))
  })

  it('assignRole() sends POST to /users/:id/roles/:roleId', async () => {
    const updated = { id: 'u1', email: 'a@b.com', is_active: true, created_at: '', roles: [] }
    const fetchMock = mockFetch(200, updated)
    vi.stubGlobal('fetch', fetchMock)

    await usersApi.assignRole('u1', 'r1')
    expect(fetchMock).toHaveBeenCalledWith('/api/users/u1/roles/r1', expect.objectContaining({ method: 'POST' }))
  })

  it('removeRole() sends DELETE to /users/:id/roles/:roleId', async () => {
    const updated = { id: 'u1', email: 'a@b.com', is_active: true, created_at: '', roles: [] }
    const fetchMock = mockFetch(200, updated)
    vi.stubGlobal('fetch', fetchMock)

    await usersApi.removeRole('u1', 'r1')
    expect(fetchMock).toHaveBeenCalledWith('/api/users/u1/roles/r1', expect.objectContaining({ method: 'DELETE' }))
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(403, {}))
    await expect(usersApi.list()).rejects.toThrow('HTTP 403')
  })

  it('returns undefined for 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.resolve(null),
    }))
    const result = await usersApi.update('u1', { is_active: false })
    expect(result).toBeUndefined()
  })
})
