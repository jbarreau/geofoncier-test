<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
</script>

<template>
  <main class="container">
    <hgroup>
      <h1>Géofoncier</h1>
      <p>Plateforme de gestion foncière</p>
    </hgroup>

    <div v-if="!auth.isAuthenticated" class="not-authenticated">
      <article>
        <hgroup>
          <h3>Connexion requise</h3>
          <p>Connectez-vous pour accéder aux fonctionnalités d'administration.</p>
        </hgroup>
        <RouterLink to="/login" role="button">Se connecter</RouterLink>
      </article>
    </div>

    <div v-else>
      <p>Bienvenue, <strong>{{ auth.email }}</strong>.</p>

      <div v-if="auth.hasPermission('users:manage')" class="grid">
        <article>
          <hgroup>
            <h3>Utilisateurs</h3>
            <p>Gérer les comptes et attribuer des rôles</p>
          </hgroup>
          <RouterLink to="/users" role="button">Ouvrir</RouterLink>
        </article>

        <article>
          <hgroup>
            <h3>Rôles</h3>
            <p>Gérer les rôles et leurs permissions</p>
          </hgroup>
          <RouterLink to="/roles" role="button">Ouvrir</RouterLink>
        </article>

        <article>
          <hgroup>
            <h3>Permissions</h3>
            <p>Gérer les permissions applicatives</p>
          </hgroup>
          <RouterLink to="/permissions" role="button">Ouvrir</RouterLink>
        </article>
      </div>

      <article v-else>
        <hgroup>
          <h3>Accès limité</h3>
          <p>Vous n'avez pas la permission <code>users:manage</code>.</p>
        </hgroup>
      </article>
    </div>
  </main>
</template>
