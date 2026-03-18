import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { rolesApi } from './roles'
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

const fakeRole = {
  id: 'r1',
  name: 'admin',
  description: null,
  created_at: '2024-01-01',
  permissions: [],
}

beforeEach(() => {
  setActivePinia(createPinia())
  const store = useAuthStore()
  store.setTokens(makeFakeJwt({ permissions: ['users:manage'] }), 'refresh')
})

describe('rolesApi.list', () => {
  it('returns list of roles', async () => {
    vi.stubGlobal('fetch', mockFetch(200, [fakeRole]))
    const result = await rolesApi.list()
    expect(result).toEqual([fakeRole])
  })
})

describe('rolesApi.get', () => {
  it('fetches a role by id', async () => {
    vi.stubGlobal('fetch', mockFetch(200, fakeRole))
    const result = await rolesApi.get('r1')
    expect(result).toEqual(fakeRole)
  })
})

describe('rolesApi.create', () => {
  it('sends POST with name and description', async () => {
    const fetchMock = mockFetch(200, fakeRole)
    vi.stubGlobal('fetch', fetchMock)
    await rolesApi.create({ name: 'admin', description: 'Admin role' })
    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(options.body).toBe(JSON.stringify({ name: 'admin', description: 'Admin role' }))
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(409, {}))
    await expect(rolesApi.create({ name: 'existing' })).rejects.toThrow('HTTP 409')
  })
})

describe('rolesApi.update', () => {
  it('sends PUT with updated fields', async () => {
    const fetchMock = mockFetch(200, { ...fakeRole, name: 'superadmin' })
    vi.stubGlobal('fetch', fetchMock)
    await rolesApi.update('r1', { name: 'superadmin' })
    const [, options] = fetchMock.mock.calls[0]
    expect(options.method).toBe('PUT')
  })
})

describe('rolesApi.delete', () => {
  it('sends DELETE and returns undefined for 204', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.resolve(null),
    }))
    const result = await rolesApi.delete('r1')
    expect(result).toBeUndefined()
  })
})

describe('rolesApi.assignPermission', () => {
  it('sends POST to /roles/:roleId/permissions/:permissionId', async () => {
    const fetchMock = mockFetch(200, fakeRole)
    vi.stubGlobal('fetch', fetchMock)
    await rolesApi.assignPermission('r1', 'p1')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/roles/r1/permissions/p1',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})

describe('rolesApi.removePermission', () => {
  it('sends DELETE to /roles/:roleId/permissions/:permissionId', async () => {
    const fetchMock = mockFetch(200, fakeRole)
    vi.stubGlobal('fetch', fetchMock)
    await rolesApi.removePermission('r1', 'p1')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/roles/r1/permissions/p1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })
})
