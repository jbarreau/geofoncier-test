import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// Mock the auth store before importing tasksApi
vi.mock('../stores/auth', () => ({
  useAuthStore: () => ({ accessToken: 'test-access-token' }),
}))

import { tasksApi } from './tasks'

function mockFetch(status: number, body?: unknown): ReturnType<typeof vi.fn> {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    statusText: status < 400 ? 'OK' : 'Error',
    json: () => Promise.resolve(body),
  })
}

describe('tasksApi', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('list calls GET /api/tasks with Authorization header', async () => {
    vi.stubGlobal('fetch', mockFetch(200, []))

    await tasksApi.list()

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/tasks',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-access-token',
        }),
      }),
    )
  })

  it('create calls POST /api/tasks with body', async () => {
    const task = { id: '1', title: 'T', description: null, status: 'todo', owner_id: 'o', due_date: null, created_at: '', updated_at: '' }
    vi.stubGlobal('fetch', mockFetch(201, task))

    const result = await tasksApi.create({ title: 'T' })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/tasks',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(result).toEqual(task)
  })

  it('update calls PATCH /api/tasks/:id', async () => {
    const task = { id: 'task-1', title: 'Updated', description: null, status: 'doing', owner_id: 'o', due_date: null, created_at: '', updated_at: '' }
    vi.stubGlobal('fetch', mockFetch(200, task))

    await tasksApi.update('task-1', { title: 'Updated' })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/tasks/task-1',
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('remove calls DELETE /api/tasks/:id and returns undefined for 204', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

    const result = await tasksApi.remove('task-1')

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/tasks/task-1',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(result).toBeUndefined()
  })

  it('throws on non-ok response', async () => {
    vi.stubGlobal('fetch', mockFetch(403, { detail: 'Forbidden' }))

    await expect(tasksApi.list()).rejects.toThrow('HTTP 403')
  })
})
