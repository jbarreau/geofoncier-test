<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import type { Task, TaskCreate, TaskUpdate } from '../api/tasks'
import TaskForm from '../components/TaskForm.vue'

const auth = useAuthStore()
const tasksStore = useTasksStore()

// --- Status filter ---
type StatusFilter = 'all' | Task['status']
const statusFilter = ref<StatusFilter>('all')

const filteredTasks = computed(() => {
  if (statusFilter.value === 'all') return tasksStore.tasks
  return tasksStore.tasks.filter((t) => t.status === statusFilter.value)
})

const statusLabel: Record<Task['status'], string> = {
  todo: 'À faire',
  doing: 'En cours',
  done: 'Terminée',
}

// --- Modal ---
const showModal = ref(false)
const editingTask = ref<Task | null>(null)

function openCreate() {
  editingTask.value = null
  showModal.value = true
}

function openEdit(task: Task) {
  editingTask.value = task
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function handleSubmit(payload: TaskCreate | TaskUpdate) {
  try {
    if (editingTask.value) {
      await tasksStore.update(editingTask.value.id, payload)
    } else {
      await tasksStore.create(payload as TaskCreate)
    }
    closeModal()
  } catch {
    // error already set in the store
  }
}

async function deleteTask(task: Task) {
  if (!confirm(`Supprimer « ${task.title} » ?`)) return
  await tasksStore.remove(task.id)
}

onMounted(() => tasksStore.fetchAll())
</script>

<template>
  <main class="container">
    <hgroup>
      <h2>Tâches</h2>
      <p>Gestion des tâches</p>
    </hgroup>

    <p v-if="tasksStore.error" role="alert" style="color: var(--pico-color-red-500)">
      {{ tasksStore.error }}
    </p>

    <!-- Toolbar -->
    <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap">
      <div role="group">
        <button
          v-for="[value, label] in [['all', 'Toutes'], ['todo', 'À faire'], ['doing', 'En cours'], ['done', 'Terminées']]"
          :key="value"
          :class="{ secondary: statusFilter !== value }"
          style="margin: 0"
          @click="statusFilter = value as StatusFilter"
        >
          {{ label }}
        </button>
      </div>

      <button
        v-if="auth.hasPermission('tasks:create')"
        data-testid="btn-create"
        style="margin: 0 0 0 auto"
        @click="openCreate"
      >
        + Nouvelle tâche
      </button>
    </div>

    <!-- Loading -->
    <div v-if="tasksStore.loading" aria-busy="true" style="text-align: center; padding: 2rem"></div>

    <template v-else>
      <p v-if="filteredTasks.length === 0" style="color: var(--pico-muted-color)">
        Aucune tâche.
      </p>

      <table v-else>
        <thead>
          <tr>
            <th>Titre</th>
            <th>Statut</th>
            <th>Échéance</th>
            <th
              v-if="auth.hasPermission('tasks:update') || auth.hasPermission('tasks:delete')"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in filteredTasks" :key="task.id">
            <td>
              <strong>{{ task.title }}</strong>
              <br v-if="task.description" />
              <small v-if="task.description" style="color: var(--pico-muted-color)">
                {{ task.description }}
              </small>
            </td>
            <td>{{ statusLabel[task.status] }}</td>
            <td>
              {{
                task.due_date
                  ? new Date(task.due_date).toLocaleDateString('fr-FR')
                  : '—'
              }}
            </td>
            <td
              v-if="auth.hasPermission('tasks:update') || auth.hasPermission('tasks:delete')"
            >
              <div role="group">
                <button
                  v-if="auth.hasPermission('tasks:update')"
                  data-testid="btn-edit"
                  class="secondary"
                  style="margin: 0"
                  @click="openEdit(task)"
                >
                  Modifier
                </button>
                <button
                  v-if="auth.hasPermission('tasks:delete')"
                  data-testid="btn-delete"
                  class="secondary"
                  style="margin: 0; color: var(--pico-color-red-500)"
                  @click="deleteTask(task)"
                >
                  Supprimer
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <TaskForm
      :open="showModal"
      :editing-task="editingTask"
      @close="closeModal"
      @submit="handleSubmit"
    />
  </main>
</template>
