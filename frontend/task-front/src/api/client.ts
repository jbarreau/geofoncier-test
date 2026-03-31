// Client HTTP de base — à étoffer selon les besoins (axios, ofetch, etc.)
// Les chemins /auth/, /tasks/, /analytics/ sont proxiés par Vite (dev)
// et par nginx (production) vers les services backend correspondants.

const BASE_URL = ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

export const api = {
  get: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'GET', ...options }),

  post: <T>(path: string, body: unknown, options?: RequestInit) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body), ...options }),

  put: <T>(path: string, body: unknown, options?: RequestInit) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body), ...options }),

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'DELETE', ...options }),
}
