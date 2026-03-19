import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTasksStore } from './tasks'
import * as tasksApiModule from '../api/tasks'
import type { Task } from '../api/tasks'

vi.mock('../api/tasks', async (importOriginal) => {
  const actual = await importOriginal<typeof tasksApiModule>()
  return {
    ...actual,
    tasksApi: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
    },
  }
})

const mockTask: Task = {
  id: 'task-1',
  title: 'Test task',
  description: null,
  status: 'todo',
  owner_id: 'owner-id',
  due_date: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

describe('useTasksStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchAll loads tasks into the store', async () => {
    vi.mocked(tasksApiModule.tasksApi.list).mockResolvedValue([mockTask])
    const store = useTasksStore()

    await store.fetchAll()

    expect(store.tasks).toEqual([mockTask])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchAll sets error on failure', async () => {
    vi.mocked(tasksApiModule.tasksApi.list).mockRejectedValue(new Error('network'))
    const store = useTasksStore()

    await store.fetchAll()

    expect(store.tasks).toEqual([])
    expect(store.error).toBe('Failed to load tasks.')
  })

  it('create prepends the new task to the list', async () => {
    const newTask = { ...mockTask, id: 'task-2', title: 'New' }
    vi.mocked(tasksApiModule.tasksApi.create).mockResolvedValue(newTask)
    const store = useTasksStore()
    store.tasks = [mockTask]

    await store.create({ title: 'New' })

    expect(store.tasks[0]).toEqual(newTask)
    expect(store.tasks).toHaveLength(2)
  })

  it('update replaces the task in the list', async () => {
    const updated = { ...mockTask, title: 'Updated', status: 'doing' as const }
    vi.mocked(tasksApiModule.tasksApi.update).mockResolvedValue(updated)
    const store = useTasksStore()
    store.tasks = [mockTask]

    await store.update('task-1', { title: 'Updated', status: 'doing' })

    expect(store.tasks[0].title).toBe('Updated')
    expect(store.tasks[0].status).toBe('doing')
  })

  it('remove filters the task out of the list', async () => {
    vi.mocked(tasksApiModule.tasksApi.remove).mockResolvedValue(undefined)
    const store = useTasksStore()
    const task2 = { ...mockTask, id: 'task-2' }
    store.tasks = [mockTask, task2]

    await store.remove('task-1')

    expect(store.tasks).toHaveLength(1)
    expect(store.tasks[0].id).toBe('task-2')
  })

  it('create sets error and re-throws on failure', async () => {
    vi.mocked(tasksApiModule.tasksApi.create).mockRejectedValue(new Error('network'))
    const store = useTasksStore()

    await expect(store.create({ title: 'New' })).rejects.toThrow()
    expect(store.error).toBe('Failed to create task.')
  })

  it('update sets error and re-throws on failure', async () => {
    vi.mocked(tasksApiModule.tasksApi.update).mockRejectedValue(new Error('network'))
    const store = useTasksStore()

    await expect(store.update('task-1', { title: 'x' })).rejects.toThrow()
    expect(store.error).toBe('Failed to update task.')
  })

  it('remove sets error and re-throws on failure', async () => {
    vi.mocked(tasksApiModule.tasksApi.remove).mockRejectedValue(new Error('network'))
    const store = useTasksStore()

    await expect(store.remove('task-1')).rejects.toThrow()
    expect(store.error).toBe('Failed to delete task.')
  })
})
