<template>
  <main class="container">
    <h1>Analytics</h1>

    <div class="analytics-grid">
      <!-- Répartition des statuts -->
      <article :aria-busy="loadingMain">
        <header><strong>Répartition des statuts</strong></header>
        <template v-if="!loadingMain">
          <p v-if="summaryError" class="error">{{ summaryError }}</p>
          <p v-else-if="!summaryData?.total" class="empty">Aucune donnée</p>
          <apexchart
            v-else
            type="donut"
            height="280"
            :options="donutOptions"
            :series="donutSeries"
          />
        </template>
      </article>

      <!-- Évolution dans le temps -->
      <article :aria-busy="loadingMain">
        <header><strong>Tâches créées (30 derniers jours)</strong></header>
        <template v-if="!loadingMain">
          <p v-if="overTimeError" class="error">{{ overTimeError }}</p>
          <p v-else-if="!overTimeData?.points.length" class="empty">Aucune donnée</p>
          <apexchart
            v-else
            type="area"
            height="280"
            :options="areaOptions"
            :series="areaSeries"
          />
        </template>
      </article>

      <!-- Tâches en retard -->
      <article :aria-busy="loadingMain" class="overdue-card">
        <header>
          <strong>Tâches en retard</strong>
          <span v-if="overdueData" class="badge">{{ overdueData.count }}</span>
        </header>
        <template v-if="!loadingMain">
          <p v-if="overdueError" class="error">{{ overdueError }}</p>
          <p v-else-if="!overdueData?.count" class="empty">Aucune tâche en retard</p>
          <div v-else class="overdue-table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Titre</th>
                  <th>Statut</th>
                  <th>Échéance</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="task in overdueData.tasks" :key="task.id">
                  <td>{{ task.title }}</td>
                  <td>
                    <span :class="['status-badge', `status-${task.status}`]">
                      {{ statusLabel(task.status) }}
                    </span>
                  </td>
                  <td>{{ formatDate(task.due_date) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </article>

      <!-- Tâches par utilisateur (admin uniquement) -->
      <article v-if="auth.hasPermission('analytics:admin')" :aria-busy="loadingByUser">
        <header><strong>Tâches par utilisateur</strong></header>
        <template v-if="!loadingByUser">
          <p v-if="byUserError" class="error">{{ byUserError }}</p>
          <p v-else-if="!byUserData?.by_user.length" class="empty">Aucune donnée</p>
          <apexchart
            v-else
            type="bar"
            height="280"
            :options="barOptions"
            :series="barSeries"
          />
        </template>
      </article>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { analyticsApi } from '../api/analytics'
import { usersApi } from '../api/users'
import type { SummaryResponse, OverdueResponse, ByUserResponse, OverTimeResponse } from '../api/analytics'

const auth = useAuthStore()

// State
const loadingMain = ref(true)
const loadingByUser = ref(false)

const summaryData = ref<SummaryResponse | null>(null)
const overdueData = ref<OverdueResponse | null>(null)
const overTimeData = ref<OverTimeResponse | null>(null)
const byUserData = ref<ByUserResponse | null>(null)
const userEmailMap = ref<Record<string, string>>({})

const summaryError = ref<string | null>(null)
const overdueError = ref<string | null>(null)
const overTimeError = ref<string | null>(null)
const byUserError = ref<string | null>(null)

// Fetch data
onMounted(async () => {
  // Load the 3 main charts in parallel
  const [summaryResult, overdueResult, overTimeResult] = await Promise.allSettled([
    analyticsApi.getSummary(),
    analyticsApi.getOverdue(),
    analyticsApi.getOverTime(),
  ])

  if (summaryResult.status === 'fulfilled') {
    summaryData.value = summaryResult.value
  } else {
    summaryError.value = 'Impossible de charger les données'
  }

  if (overdueResult.status === 'fulfilled') {
    overdueData.value = overdueResult.value
  } else {
    overdueError.value = 'Impossible de charger les données'
  }

  if (overTimeResult.status === 'fulfilled') {
    overTimeData.value = overTimeResult.value
  } else {
    overTimeError.value = 'Impossible de charger les données'
  }

  loadingMain.value = false

  // Load by-user chart + user list in parallel (requires analytics:admin = also has users:manage)
  if (auth.hasPermission('analytics:admin')) {
    loadingByUser.value = true
    try {
      const [byUserResult, usersResult] = await Promise.allSettled([
        analyticsApi.getByUser(),
        usersApi.list(),
      ])
      if (byUserResult.status === 'fulfilled') {
        byUserData.value = byUserResult.value
      } else {
        byUserError.value = 'Impossible de charger les données'
      }
      if (usersResult.status === 'fulfilled') {
        userEmailMap.value = Object.fromEntries(usersResult.value.map(u => [u.id, u.email]))
      }
    } finally {
      loadingByUser.value = false
    }
  }
})

// Helpers
function statusLabel(status: string): string {
  const labels: Record<string, string> = { todo: 'À faire', doing: 'En cours', done: 'Terminé' }
  return labels[status] ?? status
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// Donut chart (status distribution)
const donutSeries = computed(() => {
  if (!summaryData.value) return []
  const order = ['todo', 'doing', 'done']
  return order.map(s => summaryData.value!.by_status.find(b => b.status === s)?.count ?? 0)
})

const donutOptions = computed(() => ({
  labels: ['À faire', 'En cours', 'Terminé'],
  colors: ['#3b82f6', '#f59e0b', '#22c55e'],
  legend: { position: 'bottom' },
  dataLabels: { enabled: true },
  plotOptions: {
    pie: { donut: { size: '60%' } },
  },
}))

// Area chart (over time)
const areaSeries = computed(() => {
  if (!overTimeData.value) return []
  return [{ name: 'Tâches créées', data: overTimeData.value.points.map(p => p.count) }]
})

const areaOptions = computed(() => ({
  colors: ['#3b82f6'],
  xaxis: {
    categories: overTimeData.value?.points.map(p => p.date) ?? [],
    labels: {
      rotate: -45,
      formatter: (val: string) => {
        if (!val) return ''
        const d = new Date(val)
        return `${d.getDate()}/${d.getMonth() + 1}`
      },
    },
  },
  yaxis: { labels: { formatter: (v: number) => String(Math.round(v)) } },
  stroke: { curve: 'smooth' },
  fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0.1 } },
  dataLabels: { enabled: false },
  tooltip: { x: { formatter: (v: string) => v } },
}))

// Bar chart (by user)
const barSeries = computed(() => {
  if (!byUserData.value) return []
  return [{ name: 'Tâches', data: byUserData.value.by_user.map(u => u.count) }]
})

const barOptions = computed(() => ({
  colors: ['#8b5cf6'],
  plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
  xaxis: {
    categories: byUserData.value?.by_user.map(u =>
      userEmailMap.value[u.owner_id] ?? u.owner_id.substring(0, 8) + '…'
    ) ?? [],
    labels: { formatter: (v: number) => String(Math.round(v)) },
  },
  dataLabels: { enabled: false },
  tooltip: {
    y: { formatter: (v: number) => `${v} tâche${v > 1 ? 's' : ''}` },
  },
}))
</script>

<style scoped>
.analytics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-top: 1rem;
}

@media (max-width: 768px) {
  .analytics-grid {
    grid-template-columns: 1fr;
  }
}

.overdue-card {
  grid-column: 1 / -1;
}

.overdue-table-wrapper {
  max-height: 300px;
  overflow-y: auto;
}

.error {
  color: var(--pico-color-red-500, #ef4444);
  font-style: italic;
}

.empty {
  color: var(--pico-muted-color, #6b7280);
  font-style: italic;
  text-align: center;
  padding: 2rem 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--pico-color-red-500, #ef4444);
  color: white;
  border-radius: 9999px;
  padding: 0.1rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  margin-left: 0.5rem;
  vertical-align: middle;
}

.status-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-todo {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-doing {
  background: #fef3c7;
  color: #92400e;
}

.status-done {
  background: #dcfce7;
  color: #166534;
}

article > header {
  display: flex;
  align-items: center;
}

</style>

<!-- Non-scoped: neutralize PicoCSS on ApexCharts toolbar -->
<style>
/*
 * Target direct children of the toolbar that are NOT the dropdown menu.
 * This resets PicoCSS on icon buttons without touching .apexcharts-menu-item,
 * which is nested inside .apexcharts-menu (not a direct child of the toolbar).
 */
.apexcharts-toolbar button,
.apexcharts-toolbar > div:not(.apexcharts-menu) {
  background-color: transparent !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  color: inherit !important;
  width: auto !important;
  height: auto !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
}

/* Dropdown menu */
.apexcharts-menu {
  background: var(--pico-card-background-color, #1e2023) !important;
  border: 1px solid var(--pico-muted-border-color, #374151) !important;
}

.apexcharts-menu-item {
  display: block !important;
  padding: 0.4rem 0.75rem !important;
  cursor: pointer !important;
}

.apexcharts-menu-item:hover {
  background: var(--pico-muted-background-color, #374151) !important;
}
</style>
