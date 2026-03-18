import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from './client'

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

describe('api.get', () => {
  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', mockFetch(200, { id: 1 }))
    const result = await api.get('/test')
    expect(result).toEqual({ id: 1 })
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(404, {}))
    await expect(api.get('/test')).rejects.toThrow('HTTP 404')
  })

  it('sends GET method', async () => {
    const fetchMock = mockFetch(200, {})
    vi.stubGlobal('fetch', fetchMock)
    await api.get('/path')
    expect(fetchMock).toHaveBeenCalledWith('/path', expect.objectContaining({ method: 'GET' }))
  })
})

describe('api.post', () => {
  it('sends POST with JSON body', async () => {
    const fetchMock = mockFetch(200, { created: true })
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.post('/path', { name: 'test' })
    expect(result).toEqual({ created: true })
    expect(fetchMock).toHaveBeenCalledWith(
      '/path',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'test' }),
      }),
    )
  })

  it('includes Content-Type header', async () => {
    const fetchMock = mockFetch(200, {})
    vi.stubGlobal('fetch', fetchMock)
    await api.post('/path', {})
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers['Content-Type']).toBe('application/json')
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(500, {}))
    await expect(api.post('/path', {})).rejects.toThrow('HTTP 500')
  })
})

describe('api.put', () => {
  it('sends PUT with JSON body', async () => {
    const fetchMock = mockFetch(200, { updated: true })
    vi.stubGlobal('fetch', fetchMock)
    const result = await api.put('/path/1', { name: 'updated' })
    expect(result).toEqual({ updated: true })
    expect(fetchMock).toHaveBeenCalledWith(
      '/path/1',
      expect.objectContaining({ method: 'PUT' }),
    )
  })
})

describe('api.delete', () => {
  it('sends DELETE request', async () => {
    const fetchMock = mockFetch(200, { deleted: true })
    vi.stubGlobal('fetch', fetchMock)
    await api.delete('/path/1')
    expect(fetchMock).toHaveBeenCalledWith(
      '/path/1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('throws on HTTP error', async () => {
    vi.stubGlobal('fetch', mockFetch(403, {}))
    await expect(api.delete('/path/1')).rejects.toThrow('HTTP 403')
  })
})
