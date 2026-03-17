import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

interface TokenPayload {
  sub: string
  email: string
  roles: string[]
  permissions: string[]
  exp: number
}

function decodeJwtPayload(token: string): TokenPayload {
  const base64 = token.split('.')[1]
  const padded = base64.replace(/-/g, '+').replace(/_/g, '/').padEnd(
    Math.ceil(base64.length / 4) * 4,
    '=',
  )
  return JSON.parse(atob(padded)) as TokenPayload
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const permissions = ref<string[]>([])
  const email = ref<string | null>(null)

  // Rehydrate from stored token on startup
  if (accessToken.value) {
    try {
      const payload = decodeJwtPayload(accessToken.value)
      permissions.value = payload.permissions
      email.value = payload.email
    } catch {
      accessToken.value = null
      refreshToken.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }

  const isAuthenticated = computed(() => accessToken.value !== null)

  function hasPermission(permission: string): boolean {
    return permissions.value.includes(permission)
  }

  function setTokens(access: string, refresh: string): void {
    const payload = decodeJwtPayload(access)
    accessToken.value = access
    refreshToken.value = refresh
    permissions.value = payload.permissions
    email.value = payload.email
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearTokens(): void {
    accessToken.value = null
    refreshToken.value = null
    permissions.value = []
    email.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return {
    accessToken,
    refreshToken,
    permissions,
    email,
    isAuthenticated,
    hasPermission,
    setTokens,
    clearTokens,
  }
})
