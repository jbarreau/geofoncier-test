<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  permissionsApi,
  type CreatePermissionPayload,
  type Permission,
  type UpdatePermissionPayload,
} from '../api/permissions'

const permissions = ref<Permission[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Create form
const createName = ref('')
const createDescription = ref('')
const creating = ref(false)

// Edit state
const editing = ref<Permission | null>(null)
const editName = ref('')
const editDescription = ref('')

async function load() {
  loading.value = true
  error.value = null
  try {
    permissions.value = await permissionsApi.list()
  } catch {
    error.value = 'Failed to load permissions.'
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!createName.value.trim()) return
  creating.value = true
  error.value = null
  try {
    const body: CreatePermissionPayload = {
      name: createName.value.trim(),
      description: createDescription.value.trim() || null,
    }
    const created = await permissionsApi.create(body)
    permissions.value.push(created)
    createName.value = ''
    createDescription.value = ''
  } catch {
    error.value = 'Failed to create permission.'
  } finally {
    creating.value = false
  }
}

function startEdit(perm: Permission) {
  editing.value = perm
  editName.value = perm.name
  editDescription.value = perm.description ?? ''
}

async function saveEdit() {
  if (!editing.value) return
  error.value = null
  const body: UpdatePermissionPayload = {
    name: editName.value.trim() || null,
    description: editDescription.value.trim() || null,
  }
  try {
    const updated = await permissionsApi.update(editing.value.id, body)
    const idx = permissions.value.findIndex((p) => p.id === updated.id)
    if (idx !== -1) permissions.value[idx] = updated
    editing.value = null
  } catch {
    error.value = 'Failed to update permission.'
  }
}

async function remove(perm: Permission) {
  if (!confirm(`Delete permission "${perm.name}"?`)) return
  error.value = null
  try {
    await permissionsApi.delete(perm.id)
    permissions.value = permissions.value.filter((p) => p.id !== perm.id)
  } catch {
    error.value = 'Failed to delete permission.'
  }
}

onMounted(load)
</script>

<template>
  <main class="container">
    <hgroup>
      <h1>Permissions</h1>
      <p>Application permission management</p>
    </hgroup>

    <p v-if="error" role="alert" class="error">{{ error }}</p>

    <!-- Add form -->
    <article>
      <header><strong>Add a permission</strong></header>
      <form @submit.prevent="create">
        <div class="grid">
          <input
            v-model="createName"
            placeholder="Nom (ex: tasks:write)"
            required
            minlength="1"
            maxlength="100"
          />
          <input
            v-model="createDescription"
            placeholder="Description (optional)"
            maxlength="500"
          />
          <button type="submit" :aria-busy="creating">Add</button>
        </div>
      </form>
    </article>

    <!-- Table -->
    <div v-if="loading" aria-busy="true" style="text-align: center; padding: 2rem" />
    <figure v-else>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="permissions.length === 0">
            <td colspan="4" style="text-align: center">No permissions defined.</td>
          </tr>
          <tr v-for="perm in permissions" :key="perm.id">
            <template v-if="editing?.id === perm.id">
              <td>
                <input v-model="editName" minlength="1" maxlength="100" />
              </td>
              <td>
                <input v-model="editDescription" maxlength="500" />
              </td>
              <td>{{ new Date(perm.created_at).toLocaleDateString('en-GB') }}</td>
              <td>
                <button @click="saveEdit" style="margin-right: 0.5rem">Save</button>
                <button class="secondary" @click="editing = null">Cancel</button>
              </td>
            </template>
            <template v-else>
              <td><code>{{ perm.name }}</code></td>
              <td>{{ perm.description ?? '—' }}</td>
              <td>{{ new Date(perm.created_at).toLocaleDateString('en-GB') }}</td>
              <td>
                <button
                  class="secondary"
                  style="margin-right: 0.5rem"
                  @click="startEdit(perm)"
                >
                  Edit
                </button>
                <button class="contrast" @click="remove(perm)">Delete</button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </figure>
  </main>
</template>

<style scoped>
.error {
  color: var(--pico-color-red-500, #e74c3c);
}
</style>
