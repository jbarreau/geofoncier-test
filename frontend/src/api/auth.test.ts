import { describe, it, expect, vi, beforeEach } from 'vitest'
import { authApi } from './auth'

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

describe('authApi.login', () => {
  it('posts credentials and returns tokens', async () => {
    const tokens = { access_token: 'acc', refresh_token: 'ref', token_type: 'bearer' }
    const fetchMock = mockFetch(200, tokens)
    vi.stubGlobal('fetch', fetchMock)

    const result = await authApi.login('user@example.com', 'password123')
    expect(result).toEqual(tokens)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'user@example.com', password: 'password123' }),
      }),
    )
  })

  it('throws on invalid credentials', async () => {
    vi.stubGlobal('fetch', mockFetch(401, {}))
    await expect(authApi.login('bad@example.com', 'wrong')).rejects.toThrow('HTTP 401')
  })
})

describe('authApi.register', () => {
  it('posts registration data and returns user', async () => {
    const user = { id: 'u1', email: 'new@example.com', is_active: true, created_at: '2024-01-01' }
    const fetchMock = mockFetch(200, user)
    vi.stubGlobal('fetch', fetchMock)

    const result = await authApi.register('new@example.com', 'pass1234')
    expect(result).toEqual(user)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/register',
      expect.objectContaining({
        body: JSON.stringify({ email: 'new@example.com', password: 'pass1234' }),
      }),
    )
  })

  it('throws when email already exists', async () => {
    vi.stubGlobal('fetch', mockFetch(409, {}))
    await expect(authApi.register('existing@example.com', 'pass')).rejects.toThrow('HTTP 409')
  })
})

describe('authApi.logout', () => {
  it('posts tokens to logout endpoint', async () => {
    const fetchMock = mockFetch(200, null)
    vi.stubGlobal('fetch', fetchMock)

    await authApi.logout('access-token', 'refresh-token')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/logout',
      expect.objectContaining({
        body: JSON.stringify({ access_token: 'access-token', refresh_token: 'refresh-token' }),
      }),
    )
  })
})
