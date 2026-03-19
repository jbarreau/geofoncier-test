<script setup lang="ts">
import type { Task, TaskCreate, TaskUpdate } from '../api/tasks'

const props = defineProps<{
  open: boolean
  editingTask: Task | null
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: TaskCreate | TaskUpdate]
}>()

import { ref, watch } from 'vue'

const formData = ref({
  title: '',
  description: '',
  status: 'todo' as Task['status'],
  due_date: '',
})

watch(
  () => props.open,
  (open) => {
    if (open) {
      if (props.editingTask) {
        formData.value = {
          title: props.editingTask.title,
          description: props.editingTask.description ?? '',
          status: props.editingTask.status,
          due_date: props.editingTask.due_date
            ? props.editingTask.due_date.substring(0, 16)
            : '',
        }
      } else {
        formData.value = { title: '', description: '', status: 'todo', due_date: '' }
      }
    }
  },
)

function submitForm() {
  if (!formData.value.title.trim()) return
  const payload: TaskCreate | TaskUpdate = {
    title: formData.value.title.trim(),
    description: formData.value.description.trim() || undefined,
    status: formData.value.status,
    due_date: formData.value.due_date
      ? new Date(formData.value.due_date).toISOString()
      : undefined,
  }
  emit('submit', payload)
}
</script>

<template>
  <dialog :open="open" @click.self="emit('close')">
    <article>
      <header>
        <button aria-label="Fermer" rel="prev" @click="emit('close')"></button>
        <h3>{{ editingTask ? 'Modifier la tâche' : 'Nouvelle tâche' }}</h3>
      </header>

      <form @submit.prevent="submitForm">
        <label>
          Titre *
          <input
            v-model="formData.title"
            type="text"
            required
            placeholder="Titre de la tâche"
            autofocus
          />
        </label>

        <label>
          Description
          <textarea
            v-model="formData.description"
            placeholder="Description (optionnelle)"
            rows="3"
          ></textarea>
        </label>

        <label>
          Statut
          <select v-model="formData.status">
            <option value="todo">À faire</option>
            <option value="doing">En cours</option>
            <option value="done">Terminée</option>
          </select>
        </label>

        <label>
          Date d'échéance
          <input v-model="formData.due_date" type="datetime-local" />
        </label>

        <footer>
          <button type="button" class="secondary" @click="emit('close')">Annuler</button>
          <button type="submit">
            {{ editingTask ? 'Enregistrer' : 'Créer' }}
          </button>
        </footer>
      </form>
    </article>
  </dialog>
</template>
