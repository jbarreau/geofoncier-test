<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import type { Task, TaskCreate, TaskUpdate } from '../api/tasks'

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
  todo: 'To do',
  doing: 'In progress',
  done: 'Done',
}

// --- Modal ---
const showModal = ref(false)
const editingTask = ref<Task | null>(null)
const formData = ref({
  title: '',
  description: '',
  status: 'todo' as Task['status'],
  due_date: '',
})

function openCreate() {
  editingTask.value = null
  formData.value = { title: '', description: '', status: 'todo', due_date: '' }
  showModal.value = true
}

function openEdit(task: Task) {
  editingTask.value = task
  formData.value = {
    title: task.title,
    description: task.description ?? '',
    status: task.status,
    due_date: task.due_date ? task.due_date.substring(0, 16) : '',
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function submitForm() {
  if (!formData.value.title.trim()) return

  const payload: TaskCreate | TaskUpdate = {
    title: formData.value.title.trim(),
    description: formData.value.description.trim() || undefined,
    status: formData.value.status,
    due_date: formData.value.due_date
      ? new Date(formData.value.due_date).toISOString()
      : undefined,
  }

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
  if (!confirm(`Delete task "${task.title}"?`)) return
  await tasksStore.remove(task.id)
}

onMounted(() => tasksStore.fetchAll())
</script>

<template>
  <main class="container">
    <hgroup>
      <h2>Tasks</h2>
      <p>Task management</p>
    </hgroup>

    <p v-if="tasksStore.error" role="alert" style="color: var(--pico-color-red-500)">
      {{ tasksStore.error }}
    </p>

    <!-- Toolbar -->
    <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap">
      <div role="group">
        <button
          v-for="[value, label] in [['all', 'All'], ['todo', 'To do'], ['doing', 'In progress'], ['done', 'Done']]"
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
        + New task
      </button>
    </div>

    <!-- Loading -->
    <div v-if="tasksStore.loading" aria-busy="true" style="text-align: center; padding: 2rem"></div>

    <template v-else>
      <p v-if="filteredTasks.length === 0" style="color: var(--pico-muted-color)">
        No tasks found.
      </p>

      <table v-else>
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Due date</th>
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
                  ? new Date(task.due_date).toLocaleDateString('en-GB')
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
                  Edit
                </button>
                <button
                  v-if="auth.hasPermission('tasks:delete')"
                  data-testid="btn-delete"
                  class="secondary"
                  style="margin: 0; color: var(--pico-color-red-500)"
                  @click="deleteTask(task)"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- Create / Edit modal -->
    <dialog :open="showModal" @click.self="closeModal">
      <article>
        <header>
          <button aria-label="Close" rel="prev" @click="closeModal"></button>
          <h3>{{ editingTask ? 'Edit task' : 'New task' }}</h3>
        </header>

        <form @submit.prevent="submitForm">
          <label>
            Title *
            <input
              v-model="formData.title"
              type="text"
              required
              placeholder="Task title"
              autofocus
            />
          </label>

          <label>
            Description
            <textarea
              v-model="formData.description"
              placeholder="Description (optional)"
              rows="3"
            ></textarea>
          </label>

          <label>
            Status
            <select v-model="formData.status">
              <option value="todo">To do</option>
              <option value="doing">In progress</option>
              <option value="done">Done</option>
            </select>
          </label>

          <label>
            Due date
            <input v-model="formData.due_date" type="datetime-local" />
          </label>

          <footer>
            <button type="button" class="secondary" @click="closeModal">Cancel</button>
            <button type="submit">
              {{ editingTask ? 'Save' : 'Create' }}
            </button>
          </footer>
        </form>
      </article>
    </dialog>
  </main>
</template>
