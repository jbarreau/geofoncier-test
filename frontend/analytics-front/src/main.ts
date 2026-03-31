import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import VueApexCharts from 'vue3-apexcharts'
import '@picocss/pico'

import App from './App.vue'
import AnalyticsView from './views/AnalyticsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: AnalyticsView }],
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(VueApexCharts)
app.mount('#app')
