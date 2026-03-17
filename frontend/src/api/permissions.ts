import { useAuthStore } from '../stores/auth'

const BASE = '/permissions'

export interface Permission {
  id: string
  name: string
  description: string | null
  created_at: string
}

export interface CreatePermissionPayload {
  name: string
  description?: string | null
}

export interface UpdatePermissionPayload {
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

export const permissionsApi = {
  list: () => request<Permission[]>(BASE),

  get: (id: string) => request<Permission>(`${BASE}/${id}`),

  create: (body: CreatePermissionPayload) =>
    request<Permission>(BASE, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  update: (id: string, body: UpdatePermissionPayload) =>
    request<Permission>(`${BASE}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  delete: (id: string) =>
    request<void>(`${BASE}/${id}`, { method: 'DELETE' }),
}
