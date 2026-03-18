import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { analyticsApi } from './analytics'
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

describe('analyticsApi — authentication', () => {
  it('getSummary() sends Authorization header when authenticated', async () => {
    const fetchMock = mockFetch(200, { total: 0, by_status: [] })
    vi.stubGlobal('fetch', fetchMock)
    const store = useAuthStore()
    store.setTokens(makeFakeJwt({ permissions: ['analytics:read'] }), 'refresh')

    await analyticsApi.getSummary()
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers['Authorization']).toBe(`Bearer ${store.accessToken}`)
  })

  it('getSummary() works without token', async () => {
    const fetchMock = mockFetch(200, { total: 0, by_status: [] })
    vi.stubGlobal('fetch', fetchMock)

    await analyticsApi.getSummary()
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers['Authorization']).toBeUndefined()
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(403, {}))
    await expect(analyticsApi.getSummary()).rejects.toThrow('HTTP 403')
  })
})

describe('analyticsApi — getSummary', () => {
  it('calls GET /api/analytics/summary', async () => {
    const body = { total: 5, by_status: [{ status: 'todo', count: 5 }] }
    const fetchMock = mockFetch(200, body)
    vi.stubGlobal('fetch', fetchMock)

    const result = await analyticsApi.getSummary()
    expect(fetchMock).toHaveBeenCalledWith('/api/analytics/summary', expect.any(Object))
    expect(result).toEqual(body)
  })
})

describe('analyticsApi — getOverdue', () => {
  it('calls GET /api/analytics/overdue with default limit', async () => {
    const body = { count: 0, tasks: [] }
    const fetchMock = mockFetch(200, body)
    vi.stubGlobal('fetch', fetchMock)

    await analyticsApi.getOverdue()
    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/analytics/overdue?limit=100')
  })

  it('calls GET /api/analytics/overdue with custom limit', async () => {
    const fetchMock = mockFetch(200, { count: 0, tasks: [] })
    vi.stubGlobal('fetch', fetchMock)

    await analyticsApi.getOverdue(50)
    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/analytics/overdue?limit=50')
  })

  it('returns overdue task list', async () => {
    const body = {
      count: 1,
      tasks: [{ id: 'abc', title: 'Test', status: 'todo', owner_id: 'u1', due_date: '2020-01-01T00:00:00Z' }],
    }
    const fetchMock = mockFetch(200, body)
    vi.stubGlobal('fetch', fetchMock)

    const result = await analyticsApi.getOverdue()
    expect(result.count).toBe(1)
    expect(result.tasks[0].title).toBe('Test')
  })
})

describe('analyticsApi — getByUser', () => {
  it('calls GET /api/analytics/by-user', async () => {
    const body = { by_user: [{ owner_id: 'u1', count: 3 }] }
    const fetchMock = mockFetch(200, body)
    vi.stubGlobal('fetch', fetchMock)

    const result = await analyticsApi.getByUser()
    expect(fetchMock).toHaveBeenCalledWith('/api/analytics/by-user', expect.any(Object))
    expect(result.by_user).toHaveLength(1)
  })
})

describe('analyticsApi — getOverTime', () => {
  it('calls GET /api/analytics/over-time with default days', async () => {
    const fetchMock = mockFetch(200, { points: [] })
    vi.stubGlobal('fetch', fetchMock)

    await analyticsApi.getOverTime()
    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/analytics/over-time?days=30')
  })

  it('calls GET /api/analytics/over-time with custom days', async () => {
    const fetchMock = mockFetch(200, { points: [] })
    vi.stubGlobal('fetch', fetchMock)

    await analyticsApi.getOverTime(7)
    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/analytics/over-time?days=7')
  })

  it('returns time-series points', async () => {
    const body = { points: [{ date: '2026-01-01', count: 3 }, { date: '2026-01-02', count: 1 }] }
    const fetchMock = mockFetch(200, body)
    vi.stubGlobal('fetch', fetchMock)

    const result = await analyticsApi.getOverTime()
    expect(result.points).toHaveLength(2)
    expect(result.points[0]).toEqual({ date: '2026-01-01', count: 3 })
  })
})
