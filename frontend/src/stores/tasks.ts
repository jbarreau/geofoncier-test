import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tasksApi, type Task, type TaskCreate, type TaskUpdate } from '../api/tasks'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref<Task[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      tasks.value = await tasksApi.list()
    } catch {
      error.value = 'Failed to load tasks.'
    } finally {
      loading.value = false
    }
  }

  async function create(body: TaskCreate): Promise<void> {
    error.value = null
    try {
      const task = await tasksApi.create(body)
      tasks.value.unshift(task)
    } catch {
      error.value = 'Failed to create task.'
      throw new Error('create failed')
    }
  }

  async function update(id: string, body: TaskUpdate): Promise<void> {
    error.value = null
    try {
      const updated = await tasksApi.update(id, body)
      const idx = tasks.value.findIndex((t) => t.id === id)
      if (idx !== -1) tasks.value[idx] = updated
    } catch {
      error.value = 'Failed to update task.'
      throw new Error('update failed')
    }
  }

  async function remove(id: string): Promise<void> {
    error.value = null
    try {
      await tasksApi.remove(id)
      tasks.value = tasks.value.filter((t) => t.id !== id)
    } catch {
      error.value = 'Failed to delete task.'
      throw new Error('remove failed')
    }
  }

  return { tasks, loading, error, fetchAll, create, update, remove }
})
