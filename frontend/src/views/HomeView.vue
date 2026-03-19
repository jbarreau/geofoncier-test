<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
</script>

<template>
  <main class="container">
    <hgroup>
      <h1>Géofoncier</h1>
      <p>Land registry management platform</p>
    </hgroup>

    <div v-if="!auth.isAuthenticated" class="not-authenticated">
      <article>
        <hgroup>
          <h3>Login required</h3>
          <p>Sign in to access the administration features.</p>
        </hgroup>
        <RouterLink to="/login" role="button">Sign in</RouterLink>
      </article>
    </div>

    <div v-else>
      <p>Welcome, <strong>{{ auth.email }}</strong>.</p>

      <div
        v-if="auth.hasPermission('tasks:read') || auth.hasPermission('analytics:read') || auth.hasPermission('users:manage')"
        class="grid"
      >
        <article v-if="auth.hasPermission('tasks:read')">
          <hgroup>
            <h3>Tasks</h3>
            <p>View and manage land registry tasks</p>
          </hgroup>
          <RouterLink to="/tasks" role="button">Open</RouterLink>
        </article>

        <article v-if="auth.hasPermission('analytics:read')">
          <hgroup>
            <h3>Analytics</h3>
            <p>View activity indicators and charts</p>
          </hgroup>
          <RouterLink to="/analytics" role="button">Open</RouterLink>
        </article>

        <template v-if="auth.hasPermission('users:manage')">
          <article>
            <hgroup>
              <h3>Users</h3>
              <p>Manage accounts and assign roles</p>
            </hgroup>
            <RouterLink to="/users" role="button">Open</RouterLink>
          </article>

          <article>
            <hgroup>
              <h3>Roles</h3>
              <p>Manage roles and their permissions</p>
            </hgroup>
            <RouterLink to="/roles" role="button">Open</RouterLink>
          </article>

          <article>
            <hgroup>
              <h3>Permissions</h3>
              <p>Manage application permissions</p>
            </hgroup>
            <RouterLink to="/permissions" role="button">Open</RouterLink>
          </article>
        </template>
      </div>

      <article v-else>
        <hgroup>
          <h3>Limited access</h3>
          <p>You do not have access to any available features.</p>
        </hgroup>
      </article>
    </div>
  </main>
</template>
