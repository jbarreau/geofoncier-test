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
    error.value = 'Failed to create account. This email may already be in use.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="container">
    <article style="max-width: 400px; margin: 4rem auto">
      <hgroup>
        <h2>Create an account</h2>
        <p>Géofoncier — sign up</p>
      </hgroup>
      <form @submit.prevent="submit">
        <label>
          Email
          <input v-model="email" type="email" required autocomplete="username" />
        </label>
        <label>
          Password
          <input
            v-model="password"
            type="password"
            required
            minlength="8"
            maxlength="128"
            autocomplete="new-password"
          />
          <small>Minimum 8 characters.</small>
        </label>
        <p v-if="error" role="alert" style="color: var(--pico-color-red-500)">{{ error }}</p>
        <button type="submit" :aria-busy="loading">Create account</button>
      </form>
      <footer>
        <small>Already have an account? <RouterLink to="/login">Sign in</RouterLink></small>
      </footer>
    </article>
  </main>
</template>
