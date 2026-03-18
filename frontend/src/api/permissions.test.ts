import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { permissionsApi } from './permissions'
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

const fakePerm = { id: 'p1', name: 'tasks:read', description: null, created_at: '2024-01-01' }

beforeEach(() => {
  setActivePinia(createPinia())
  const store = useAuthStore()
  store.setTokens(makeFakeJwt({ permissions: ['users:manage'] }), 'refresh')
})

describe('permissionsApi.list', () => {
  it('returns list of permissions', async () => {
    vi.stubGlobal('fetch', mockFetch(200, [fakePerm]))
    const result = await permissionsApi.list()
    expect(result).toEqual([fakePerm])
  })
})

describe('permissionsApi.get', () => {
  it('fetches a single permission by id', async () => {
    vi.stubGlobal('fetch', mockFetch(200, fakePerm))
    const result = await permissionsApi.get('p1')
    expect(result).toEqual(fakePerm)
  })
})

describe('permissionsApi.create', () => {
  it('sends POST with name and description', async () => {
    const fetchMock = mockFetch(200, fakePerm)
    vi.stubGlobal('fetch', fetchMock)
    await permissionsApi.create({ name: 'tasks:read', description: 'Read tasks' })
    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(options.body).toBe(JSON.stringify({ name: 'tasks:read', description: 'Read tasks' }))
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(400, {}))
    await expect(permissionsApi.create({ name: '' })).rejects.toThrow('HTTP 400')
  })
})

describe('permissionsApi.update', () => {
  it('sends PUT with updated fields', async () => {
    const fetchMock = mockFetch(200, { ...fakePerm, name: 'tasks:write' })
    vi.stubGlobal('fetch', fetchMock)
    const result = await permissionsApi.update('p1', { name: 'tasks:write' })
    expect(result).toEqual({ ...fakePerm, name: 'tasks:write' })
    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('PUT')
  })
})

describe('permissionsApi.delete', () => {
  it('sends DELETE and returns undefined for 204', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.resolve(null),
    }))
    const result = await permissionsApi.delete('p1')
    expect(result).toBeUndefined()
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(404, {}))
    await expect(permissionsApi.delete('p1')).rejects.toThrow('HTTP 404')
  })
})
