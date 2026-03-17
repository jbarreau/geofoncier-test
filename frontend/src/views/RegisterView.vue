<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../api/auth'

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

const router = useRouter()

async function submit() {
  loading.value = true
  error.value = null
  try {
    await authApi.register(email.value, password.value)
    await router.push({ name: 'login' })
  } catch {
    error.value = 'Impossible de créer le compte. Cet email est peut-être déjà utilisé.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="container">
    <article style="max-width: 400px; margin: 4rem auto">
      <hgroup>
        <h2>Créer un compte</h2>
        <p>Géofoncier — inscription</p>
      </hgroup>
      <form @submit.prevent="submit">
        <label>
          Email
          <input v-model="email" type="email" required autocomplete="username" />
        </label>
        <label>
          Mot de passe
          <input
            v-model="password"
            type="password"
            required
            minlength="8"
            maxlength="128"
            autocomplete="new-password"
          />
          <small>Minimum 8 caractères.</small>
        </label>
        <p v-if="error" role="alert" style="color: var(--pico-color-red-500)">{{ error }}</p>
        <button type="submit" :aria-busy="loading">Créer le compte</button>
      </form>
      <footer>
        <small>Déjà un compte ? <RouterLink to="/login">Se connecter</RouterLink></small>
      </footer>
    </article>
  </main>
</template>
