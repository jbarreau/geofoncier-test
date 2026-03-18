import { useAuthStore } from '../stores/auth'

const BASE = '/api/analytics'

export interface StatusCount {
  status: string
  count: number
}

export interface SummaryResponse {
  total: number
  by_status: StatusCount[]
}

export interface OverdueTask {
  id: string
  title: string
  status: string
  owner_id: string
  due_date: string
}

export interface OverdueResponse {
  count: number
  tasks: OverdueTask[]
}

export interface UserTaskCount {
  owner_id: string
  count: number
}

export interface ByUserResponse {
  by_user: UserTaskCount[]
}

export interface TimePoint {
  date: string
  count: number
}

export interface OverTimeResponse {
  points: TimePoint[]
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

  return response.json() as Promise<T>
}

export const analyticsApi = {
  getSummary: () => request<SummaryResponse>(`${BASE}/summary`),

  getOverdue: (limit = 100) => request<OverdueResponse>(`${BASE}/overdue?limit=${limit}`),

  getByUser: () => request<ByUserResponse>(`${BASE}/by-user`),

  getOverTime: (days = 30) => request<OverTimeResponse>(`${BASE}/over-time?days=${days}`),
}
