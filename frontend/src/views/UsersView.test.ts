import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import UsersView from './UsersView.vue'
import * as usersModule from '../api/users'
import * as rolesModule from '../api/roles'

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/users', component: UsersView }],
})

const fakeRole = { id: 'r1', name: 'admin', description: null, created_at: '', permissions: [] }
const fakeRole2 = { id: 'r2', name: 'viewer', description: null, created_at: '', permissions: [] }

const fakeUser = {
  id: 'u1',
  email: 'alice@test.com',
  is_active: true,
  created_at: '',
  roles: [],
}

const fakeUserWithRole = { ...fakeUser, roles: [fakeRole] }

function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(UsersView, { global: { plugins: [router, pinia] } })
}

beforeEach(async () => {
  vi.restoreAllMocks()
  await router.push('/users')
})

describe('UsersView', () => {
  it('loads users and roles on mount', async () => {
    vi.spyOn(usersModule.usersApi, 'list').mockResolvedValue([fakeUser])
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('alice@test.com')
  })

  it('shows error when loading fails', async () => {
    vi.spyOn(usersModule.usersApi, 'list').mockRejectedValue(new Error('Network'))
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Failed to load data')
  })

  it('shows empty state when no users', async () => {
    vi.spyOn(usersModule.usersApi, 'list').mockResolvedValue([])
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('No users found')
  })

  it('toggleActive calls usersApi.update with inverted is_active', async () => {
    vi.spyOn(usersModule.usersApi, 'list').mockResolvedValue([fakeUser])
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])
    vi.spyOn(usersModule.usersApi, 'update').mockResolvedValue({ ...fakeUser, is_active: false })

    const wrapper = mountView()
    await flushPromises()

    const statusBtn = wrapper.find('button')
    await statusBtn.trigger('click')
    await flushPromises()

    expect(usersModule.usersApi.update).toHaveBeenCalledWith('u1', { is_active: false })
  })

  it('displays user status correctly (Actif/Inactif)', async () => {
    const inactiveUser = { ...fakeUser, id: 'u2', email: 'bob@test.com', is_active: false }
    vi.spyOn(usersModule.usersApi, 'list').mockResolvedValue([fakeUser, inactiveUser])
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Active')
    expect(wrapper.text()).toContain('Inactive')
  })

  it('shows role badges and unassigned roles dropdown', async () => {
    vi.spyOn(usersModule.usersApi, 'list').mockResolvedValue([fakeUserWithRole])
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole, fakeRole2])

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('admin')
    const options = wrapper.findAll('option')
    expect(options.some((o) => o.text().includes('viewer'))).toBe(true)
  })

  it('assignRole calls usersApi.assignRole', async () => {
    vi.spyOn(usersModule.usersApi, 'list').mockResolvedValue([fakeUser])
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole])
    vi.spyOn(usersModule.usersApi, 'assignRole').mockResolvedValue(fakeUserWithRole)

    const wrapper = mountView()
    await flushPromises()

    const select = wrapper.find('select')
    await select.setValue('r1')
    await select.trigger('change')
    await flushPromises()

    expect(usersModule.usersApi.assignRole).toHaveBeenCalledWith('u1', 'r1')
  })

  it('removeRole calls usersApi.removeRole when clicking role badge', async () => {
    vi.spyOn(usersModule.usersApi, 'list').mockResolvedValue([fakeUserWithRole])
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole])
    vi.spyOn(usersModule.usersApi, 'removeRole').mockResolvedValue({ ...fakeUserWithRole, roles: [] })

    const wrapper = mountView()
    await flushPromises()

    const roleBadge = wrapper.find('kbd')
    await roleBadge.trigger('click')
    await flushPromises()

    expect(usersModule.usersApi.removeRole).toHaveBeenCalledWith('u1', 'r1')
  })
})
