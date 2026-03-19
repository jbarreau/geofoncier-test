<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { rolesApi, type Role } from '../api/roles'
import { permissionsApi, type Permission } from '../api/permissions'

const roles = ref<Role[]>([])
const allPermissions = ref<Permission[]>([])
const error = ref<string | null>(null)
const loading = ref(false)

// Create form
const newName = ref('')
const newDescription = ref('')
const creating = ref(false)

// Edit state
const editingId = ref<string | null>(null)
const editName = ref('')
const editDescription = ref('')

async function load() {
  loading.value = true
  error.value = null
  try {
    const [fetchedRoles, fetchedPermissions] = await Promise.all([
      rolesApi.list(),
      permissionsApi.list(),
    ])
    roles.value = fetchedRoles
    allPermissions.value = fetchedPermissions
  } catch {
    error.value = 'Failed to load data.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function createRole() {
  if (!newName.value.trim()) return
  creating.value = true
  error.value = null
  try {
    const role = await rolesApi.create({
      name: newName.value.trim(),
      description: newDescription.value.trim() || null,
    })
    roles.value.push(role)
    newName.value = ''
    newDescription.value = ''
  } catch {
    error.value = 'Failed to create role. The name may already exist.'
  } finally {
    creating.value = false
  }
}

function startEdit(role: Role) {
  editingId.value = role.id
  editName.value = role.name
  editDescription.value = role.description ?? ''
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(role: Role) {
  error.value = null
  try {
    const updated = await rolesApi.update(role.id, {
      name: editName.value.trim() || null,
      description: editDescription.value.trim() || null,
    })
    const idx = roles.value.findIndex((r) => r.id === role.id)
    if (idx !== -1) roles.value[idx] = updated
    editingId.value = null
  } catch {
    error.value = 'Failed to update role.'
  }
}

async function deleteRole(role: Role) {
  if (!confirm(`Delete role "${role.name}"?`)) return
  error.value = null
  try {
    await rolesApi.delete(role.id)
    roles.value = roles.value.filter((r) => r.id !== role.id)
  } catch {
    error.value = 'Failed to delete role.'
  }
}

async function assignPermission(role: Role, permissionId: string) {
  try {
    const updated = await rolesApi.assignPermission(role.id, permissionId)
    const idx = roles.value.findIndex((r) => r.id === role.id)
    if (idx !== -1) roles.value[idx] = updated
  } catch {
    error.value = 'Failed to assign permission.'
  }
}

async function removePermission(role: Role, permissionId: string) {
  try {
    const updated = await rolesApi.removePermission(role.id, permissionId)
    const idx = roles.value.findIndex((r) => r.id === role.id)
    if (idx !== -1) roles.value[idx] = updated
  } catch {
    error.value = 'Failed to remove permission.'
  }
}

function unassignedPermissions(role: Role): Permission[] {
  const assigned = new Set(role.permissions.map((p) => p.id))
  return allPermissions.value.filter((p) => !assigned.has(p.id))
}
</script>

<template>
  <main class="container">
    <hgroup>
      <h2>Roles</h2>
      <p>Role management and permission assignment</p>
    </hgroup>

    <p v-if="error" role="alert" style="color: var(--pico-color-red-500)">{{ error }}</p>

    <!-- Create form -->
    <article>
      <h4>New role</h4>
      <form @submit.prevent="createRole" style="display: flex; gap: 0.5rem; align-items: flex-end">
        <label style="flex: 1; margin: 0">
          Name
          <input v-model="newName" type="text" required placeholder="e.g. admin" />
        </label>
        <label style="flex: 2; margin: 0">
          Description
          <input v-model="newDescription" type="text" placeholder="Optional" />
        </label>
        <button type="submit" :aria-busy="creating" style="margin: 0; align-self: flex-end">
          Create
        </button>
      </form>
    </article>

    <div v-if="loading" aria-busy="true" style="text-align: center; padding: 2rem"></div>

    <template v-else>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Permissions</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="role in roles" :key="role.id">
            <template v-if="editingId === role.id">
              <td><input v-model="editName" type="text" style="margin: 0" /></td>
              <td>
                <input v-model="editDescription" type="text" placeholder="—" style="margin: 0" />
              </td>
              <td colspan="2">
                <button class="secondary" style="margin: 0 0.5rem 0 0" @click="saveEdit(role)">
                  Save
                </button>
                <button class="outline secondary" style="margin: 0" @click="cancelEdit">
                  Cancel
                </button>
              </td>
            </template>

            <template v-else>
              <td>
                <strong>{{ role.name }}</strong>
              </td>
              <td>{{ role.description ?? '—' }}</td>
              <td>
                <span v-if="role.permissions.length === 0" style="color: var(--pico-muted-color)">
                  None
                </span>
                <span
                  v-for="perm in role.permissions"
                  :key="perm.id"
                  style="margin-right: 0.5rem"
                >
                  <kbd style="cursor: pointer" @click="removePermission(role, perm.id)"
                    >{{ perm.name }} ✕</kbd
                  >
                </span>
                <select
                  v-if="unassignedPermissions(role).length"
                  style="margin: 0.25rem 0 0; padding: 0.2rem 0.4rem; font-size: 0.8rem; display: inline-block; width: auto"
                  @change="
                    (e) => {
                      const val = (e.target as HTMLSelectElement).value
                      if (val) {
                        assignPermission(role, val)
                        ;(e.target as HTMLSelectElement).value = ''
                      }
                    }
                  "
                >
                  <option value="">+ Permission</option>
                  <option
                    v-for="perm in unassignedPermissions(role)"
                    :key="perm.id"
                    :value="perm.id"
                  >
                    {{ perm.name }}
                  </option>
                </select>
              </td>
              <td style="white-space: nowrap">
                <button
                  class="outline"
                  style="margin: 0 0.5rem 0 0; padding: 0.25rem 0.75rem; font-size: 0.85rem"
                  @click="startEdit(role)"
                >
                  Edit
                </button>
                <button
                  class="outline contrast"
                  style="margin: 0; padding: 0.25rem 0.75rem; font-size: 0.85rem"
                  @click="deleteRole(role)"
                >
                  Delete
                </button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
      <p v-if="roles.length === 0" style="text-align: center; color: var(--pico-muted-color)">
        No roles found.
      </p>
    </template>
  </main>
</template>
