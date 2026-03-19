import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { tasksApi } from '../api/tasks'
import type { Task } from '../api/tasks'
import TasksView from './TasksView.vue'

vi.mock('../api/tasks', () => ({
  tasksApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}))

const mockTask: Task = {
  id: 'task-1',
  title: 'Verify boundary markers',
  description: null,
  status: 'todo',
  owner_id: 'owner-id',
  due_date: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function makeToken(permissions: string[], roles: string[] = []): string {
  const header = btoa(JSON.stringify({ alg: 'RS256' }))
  const body = btoa(
    JSON.stringify({ sub: 'user-id', email: 'test@example.com', roles, permissions, exp: 9999999999 }),
  )
  return `${header}.${body}.sig`
}

function mountWith(permissions: string[], roles: string[] = []) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.setTokens(makeToken(permissions, roles), 'refresh')
  return mount(TasksView, { global: { plugins: [pinia] } })
}

describe('TasksView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tasksApi.list).mockResolvedValue([])
  })

  it('calls fetchAll on mount', async () => {
    mountWith(['tasks:read'])
    await flushPromises()

    expect(tasksApi.list).toHaveBeenCalledOnce()
  })

  it('shows "No tasks found" when list is empty', async () => {
    vi.mocked(tasksApi.list).mockResolvedValue([])
    const wrapper = mountWith(['tasks:read'])
    await flushPromises()

    expect(wrapper.text()).toContain('No tasks found')
  })

  it('shows "New task" button for user with tasks:create', async () => {
    const wrapper = mountWith(['tasks:create', 'tasks:read'])
    await flushPromises()

    expect(wrapper.find('[data-testid="btn-create"]').exists()).toBe(true)
  })

  it('hides "New task" button for viewer without tasks:create', async () => {
    const wrapper = mountWith(['tasks:read'], ['viewer'])
    await flushPromises()

    expect(wrapper.find('[data-testid="btn-create"]').exists()).toBe(false)
  })

  it('shows edit button for user with tasks:update', async () => {
    vi.mocked(tasksApi.list).mockResolvedValue([mockTask])
    const wrapper = mountWith(['tasks:read', 'tasks:update'])
    await flushPromises()

    expect(wrapper.find('[data-testid="btn-edit"]').exists()).toBe(true)
  })

  it('hides edit button for viewer without tasks:update', async () => {
    vi.mocked(tasksApi.list).mockResolvedValue([mockTask])
    const wrapper = mountWith(['tasks:read'], ['viewer'])
    await flushPromises()

    expect(wrapper.find('[data-testid="btn-edit"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="btn-delete"]').exists()).toBe(false)
  })

  it('shows delete button for admin with tasks:delete', async () => {
    vi.mocked(tasksApi.list).mockResolvedValue([mockTask])
    const wrapper = mountWith(['tasks:read', 'tasks:update', 'tasks:delete'], ['admin'])
    await flushPromises()

    expect(wrapper.find('[data-testid="btn-delete"]').exists()).toBe(true)
  })
})
