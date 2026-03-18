<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usersApi, type User } from '../api/users'
import { rolesApi, type Role } from '../api/roles'

const users = ref<User[]>([])
const roles = ref<Role[]>([])
const error = ref<string | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [fetchedUsers, fetchedRoles] = await Promise.all([usersApi.list(), rolesApi.list()])
    users.value = fetchedUsers
    roles.value = fetchedRoles
  } catch {
    error.value = 'Impossible de charger les données.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function toggleActive(user: User) {
  try {
    const updated = await usersApi.update(user.id, { is_active: !user.is_active })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
  } catch {
    error.value = "Impossible de modifier l'utilisateur."
  }
}

async function assignRole(user: User, roleId: string) {
  if (user.roles.some((r) => r.id === roleId)) return
  try {
    const updated = await usersApi.assignRole(user.id, roleId)
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
  } catch {
    error.value = "Impossible d'assigner le rôle."
  }
}

async function removeRole(user: User, roleId: string) {
  try {
    const updated = await usersApi.removeRole(user.id, roleId)
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) users.value[idx] = updated
  } catch {
    error.value = 'Impossible de retirer le rôle.'
  }
}

function unassignedRoles(user: User): Role[] {
  const assigned = new Set(user.roles.map((r) => r.id))
  return roles.value.filter((r) => !assigned.has(r.id))
}
</script>

<template>
  <main class="container">
    <hgroup>
      <h2>Utilisateurs</h2>
      <p>Gestion des comptes et attribution des rôles</p>
    </hgroup>

    <p v-if="error" role="alert" style="color: var(--pico-color-red-500)">{{ error }}</p>

    <div v-if="loading" aria-busy="true" style="text-align: center; padding: 2rem"></div>

    <template v-else>
      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Statut</th>
            <th>Rôles</th>
            <th>Ajouter un rôle</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.email }}</td>
            <td>
              <button
                :class="user.is_active ? 'secondary' : 'contrast'"
                style="margin: 0; padding: 0.25rem 0.75rem; font-size: 0.85rem"
                @click="toggleActive(user)"
              >
                {{ user.is_active ? 'Actif' : 'Inactif' }}
              </button>
            </td>
            <td>
              <span v-if="user.roles.length === 0" style="color: var(--pico-muted-color)">
                Aucun
              </span>
              <span v-for="role in user.roles" :key="role.id" style="margin-right: 0.5rem">
                <kbd style="cursor: pointer" @click="removeRole(user, role.id)"
                  >{{ role.name }} ✕</kbd
                >
              </span>
            </td>
            <td>
              <select
                v-if="unassignedRoles(user).length"
                style="margin: 0; padding: 0.25rem 0.5rem; font-size: 0.85rem"
                @change="
                  (e) => {
                    const val = (e.target as HTMLSelectElement).value
                    if (val) {
                      assignRole(user, val)
                      ;(e.target as HTMLSelectElement).value = ''
                    }
                  }
                "
              >
                <option value="">— Assigner —</option>
                <option v-for="role in unassignedRoles(user)" :key="role.id" :value="role.id">
                  {{ role.name }}
                </option>
              </select>
              <span v-else style="color: var(--pico-muted-color)">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="users.length === 0" style="text-align: center; color: var(--pico-muted-color)">
        Aucun utilisateur.
      </p>
    </template>
  </main>
</template>
