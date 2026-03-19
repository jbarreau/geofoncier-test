import { useAuthStore } from '../stores/auth'

const BASE = '/api/roles'

export interface Permission {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface Role {
  id: string
  name: string
  description: string | null
  created_at: string
  permissions: Permission[]
}

export interface CreateRolePayload {
  name: string
  description?: string | null
}

export interface UpdateRolePayload {
  name?: string | null
  description?: string | null
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

export const rolesApi = {
  list: () => request<Role[]>(BASE),

  get: (id: string) => request<Role>(`${BASE}/${id}`),

  create: (body: CreateRolePayload) =>
    request<Role>(BASE, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  update: (id: string, body: UpdateRolePayload) =>
    request<Role>(`${BASE}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  delete: (id: string) => request<void>(`${BASE}/${id}`, { method: 'DELETE' }),

  assignPermission: (roleId: string, permissionId: string) =>
    request<Role>(`${BASE}/${roleId}/permissions/${permissionId}`, { method: 'POST' }),

  removePermission: (roleId: string, permissionId: string) =>
    request<Role>(`${BASE}/${roleId}/permissions/${permissionId}`, { method: 'DELETE' }),
}
