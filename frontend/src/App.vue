<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { authApi } from './api/auth'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function logout() {
  if (auth.accessToken && auth.refreshToken) {
    try {
      await authApi.logout(auth.accessToken, auth.refreshToken)
    } catch {
      // ignore logout errors — clear tokens regardless
    }
  }
  auth.clearTokens()
  router.push('/login')
}
</script>

<template>
  <nav class="container-fluid">
    <ul>
      <li><strong><RouterLink to="/">Géofoncier</RouterLink></strong></li>
    </ul>
    <ul>
      <li v-if="auth.isAuthenticated && auth.hasPermission('analytics:read')">
        <RouterLink to="/analytics">Analytics</RouterLink>
      </li>
      <li v-if="auth.isAuthenticated && auth.hasPermission('users:manage')">
        <RouterLink to="/users">Utilisateurs</RouterLink>
      </li>
      <li v-if="auth.isAuthenticated && auth.hasPermission('users:manage')">
        <RouterLink to="/roles">Rôles</RouterLink>
      </li>
      <li v-if="auth.isAuthenticated && auth.hasPermission('users:manage')">
        <RouterLink to="/permissions">Permissions</RouterLink>
      </li>
      <li v-if="auth.isAuthenticated">
        <small>{{ auth.email }}</small>
      </li>
      <li v-if="auth.isAuthenticated">
        <button class="secondary" style="margin: 0" @click="logout">Déconnexion</button>
      </li>
      <li v-else>
        <RouterLink to="/login" role="button" class="secondary">Connexion</RouterLink>
      </li>
    </ul>
  </nav>
  <RouterView />
</template>
