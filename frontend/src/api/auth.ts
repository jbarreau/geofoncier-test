import { api } from './client'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/api/auth/login', { email, password }),

  logout: (access_token: string, refresh_token: string) =>
    api.post<void>('/api/auth/logout', { access_token, refresh_token }),
}
