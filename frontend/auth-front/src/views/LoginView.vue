<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

async function submit() {
  loading.value = true
  error.value = null
  try {
    const data = await authApi.login(email.value, password.value)
    auth.setTokens(data.access_token, data.refresh_token)
    const redirect = (route.query.redirect as string) ?? '/'
    await router.push(redirect)
  } catch {
    error.value = 'Identifiants invalides.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="container">
    <article style="max-width: 400px; margin: 4rem auto">
      <hgroup>
        <h2>Connexion</h2>
        <p>Géofoncier — espace administration</p>
      </hgroup>
      <form @submit.prevent="submit">
        <label>
          Email
          <input v-model="email" type="email" required autocomplete="username" />
        </label>
        <label>
          Mot de passe
          <input v-model="password" type="password" required autocomplete="current-password" />
        </label>
        <p v-if="error" role="alert" style="color: var(--pico-color-red-500)">{{ error }}</p>
        <button type="submit" :aria-busy="loading">Se connecter</button>
      </form>
      <footer>
        <small>Pas encore de compte ? <RouterLink to="/register">Créer un compte</RouterLink></small>
      </footer>
    </article>
  </main>
</template>
