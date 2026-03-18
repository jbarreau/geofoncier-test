import { useAuthStore } from '../stores/auth'

const BASE = '/api/tasks'

export interface Task {
  id: string
  title: string
  description: string | null
  status: 'todo' | 'doing' | 'done'
  owner_id: string
  due_date: string | null
  created_at: string
  updated_at: string
}

export interface TaskCreate {
  title: string
  description?: string
  status?: Task['status']
  due_date?: string
}

export interface TaskUpdate {
  title?: string
  description?: string
  status?: Task['status']
  due_date?: string
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const store = useAuthStore()
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(store.accessToken ? { Authorization: `Bearer ${store.accessToken}` } : {}),
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const tasksApi = {
  list: () => request<Task[]>(BASE),

  get: (id: string) => request<Task>(`${BASE}/${id}`),

  create: (body: TaskCreate) =>
    request<Task>(BASE, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  update: (id: string, body: TaskUpdate) =>
    request<Task>(`${BASE}/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  remove: (id: string) =>
    request<void>(`${BASE}/${id}`, { method: 'DELETE' }),
}
