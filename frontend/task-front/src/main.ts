import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import '@picocss/pico'

import App from './App.vue'
import TasksView from './views/TasksView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: TasksView }],
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
