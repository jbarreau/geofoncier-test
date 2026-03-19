import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import AnalyticsView from './AnalyticsView.vue'
import { useAuthStore } from '../stores/auth'
import { makeFakeJwt } from '../__tests__/helpers'
import * as analyticsModule from '../api/analytics'
import * as usersModule from '../api/users'

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/analytics', component: AnalyticsView }],
})

// Stub <apexchart> — avoids needing the full ApexCharts global registration in tests
const apexchartStub = { template: '<div class="apexchart-stub" />' }

function mountAnalytics(permissions: string[] = ['analytics:read']) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useAuthStore()
  store.setTokens(makeFakeJwt({ permissions }), 'refresh')
  return mount(AnalyticsView, {
    global: {
      plugins: [router, pinia],
      stubs: { apexchart: apexchartStub },
    },
  })
}

const SUMMARY = { total: 10, by_status: [{ status: 'todo', count: 6 }, { status: 'doing', count: 3 }, { status: 'done', count: 1 }] }
const OVERDUE = { count: 2, tasks: [
  { id: 'a', title: 'Tâche A', status: 'todo', owner_id: 'u1', due_date: '2020-01-01T00:00:00Z' },
  { id: 'b', title: 'Tâche B', status: 'doing', owner_id: 'u2', due_date: '2020-06-01T00:00:00Z' },
]}
const OVER_TIME = { points: [{ date: '2026-02-01', count: 2 }, { date: '2026-02-02', count: 1 }] }
const BY_USER = { by_user: [{ owner_id: 'u1', count: 5 }, { owner_id: 'u2', count: 3 }] }
const USERS = [{ id: 'u1', email: 'alice@test.com', is_active: true, created_at: '', roles: [] }]

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('AnalyticsView — loading state', () => {
  it('shows aria-busy while fetching', () => {
    vi.spyOn(analyticsModule, 'analyticsApi', 'get').mockReturnValue({
      getSummary: () => new Promise(() => {}),
      getOverdue: () => new Promise(() => {}),
      getOverTime: () => new Promise(() => {}),
      getByUser: () => new Promise(() => {}),
    })
    const wrapper = mountAnalytics()
    const busyArticles = wrapper.findAll('[aria-busy="true"]')
    expect(busyArticles.length).toBeGreaterThan(0)
  })
})

describe('AnalyticsView — data display', () => {
  beforeEach(() => {
    vi.spyOn(analyticsModule, 'analyticsApi', 'get').mockReturnValue({
      getSummary: vi.fn().mockResolvedValue(SUMMARY),
      getOverdue: vi.fn().mockResolvedValue(OVERDUE),
      getOverTime: vi.fn().mockResolvedValue(OVER_TIME),
      getByUser: vi.fn().mockResolvedValue(BY_USER),
    })
    vi.spyOn(usersModule, 'usersApi', 'get').mockReturnValue({
      list: vi.fn().mockResolvedValue(USERS),
      get: vi.fn(),
      update: vi.fn(),
      assignRole: vi.fn(),
      removeRole: vi.fn(),
    })
  })

  it('renders the page title', async () => {
    const wrapper = mountAnalytics()
    await flushPromises()
    expect(wrapper.text()).toContain('Analytics')
  })

  it('renders overdue tasks in the table', async () => {
    const wrapper = mountAnalytics()
    await flushPromises()
    expect(wrapper.text()).toContain('Tâche A')
    expect(wrapper.text()).toContain('Tâche B')
  })

  it('renders the overdue badge count', async () => {
    const wrapper = mountAnalytics()
    await flushPromises()
    expect(wrapper.find('.badge').text()).toBe('2')
  })

  it('renders chart stubs after loading', async () => {
    const wrapper = mountAnalytics()
    await flushPromises()
    expect(wrapper.findAll('.apexchart-stub').length).toBeGreaterThan(0)
  })

  it('hides by-user chart for analytics:read only user', async () => {
    const wrapper = mountAnalytics(['analytics:read'])
    await flushPromises()
    // by-user section rendered with v-if="auth.hasPermission('analytics:admin')"
    const headers = wrapper.findAll('article header strong')
    const texts = headers.map(h => h.text())
    expect(texts).not.toContain('Tasks by user')
  })

  it('shows by-user chart for analytics:admin user', async () => {
    const wrapper = mountAnalytics(['analytics:read', 'analytics:admin', 'users:manage'])
    await flushPromises()
    expect(wrapper.text()).toContain('Tasks by user')
  })
})

describe('AnalyticsView — error handling', () => {
  it('shows error message when summary fetch fails', async () => {
    vi.spyOn(analyticsModule, 'analyticsApi', 'get').mockReturnValue({
      getSummary: vi.fn().mockRejectedValue(new Error('Network error')),
      getOverdue: vi.fn().mockResolvedValue(OVERDUE),
      getOverTime: vi.fn().mockResolvedValue(OVER_TIME),
      getByUser: vi.fn().mockResolvedValue(BY_USER),
    })
    const wrapper = mountAnalytics()
    await flushPromises()
    expect(wrapper.text()).toContain('Failed to load data')
  })

  it('shows empty state when no overdue tasks', async () => {
    vi.spyOn(analyticsModule, 'analyticsApi', 'get').mockReturnValue({
      getSummary: vi.fn().mockResolvedValue(SUMMARY),
      getOverdue: vi.fn().mockResolvedValue({ count: 0, tasks: [] }),
      getOverTime: vi.fn().mockResolvedValue(OVER_TIME),
      getByUser: vi.fn().mockResolvedValue(BY_USER),
    })
    const wrapper = mountAnalytics()
    await flushPromises()
    expect(wrapper.text()).toContain('No overdue tasks')
  })
})
