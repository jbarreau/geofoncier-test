import { useAuthStore } from '../stores/auth'

const BASE = '/api/users'

export interface Role {
  id: string
  name: string
  description: string | null
  created_at: string
  permissions: Permission[]
}

export interface Permission {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface User {
  id: string
  email: string
  is_active: boolean
  created_at: string
  roles: Role[]
}

export interface UpdateUserPayload {
  is_active?: boolean
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

export const usersApi = {
  list: () => request<User[]>(BASE),

  get: (id: string) => request<User>(`${BASE}/${id}`),

  update: (id: string, body: UpdateUserPayload) =>
    request<User>(`${BASE}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  assignRole: (userId: string, roleId: string) =>
    request<User>(`${BASE}/${userId}/roles/${roleId}`, { method: 'POST' }),

  removeRole: (userId: string, roleId: string) =>
    request<User>(`${BASE}/${userId}/roles/${roleId}`, { method: 'DELETE' }),
}
