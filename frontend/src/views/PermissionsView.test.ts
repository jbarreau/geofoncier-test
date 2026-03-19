import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import PermissionsView from './PermissionsView.vue'
import * as permApi from '../api/permissions'

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/permissions', component: PermissionsView }],
})

const fakePerm = { id: 'p1', name: 'tasks:read', description: 'Read tasks', created_at: '2024-01-01' }
const fakePerm2 = { id: 'p2', name: 'tasks:write', description: null, created_at: '2024-01-01' }

function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(PermissionsView, { global: { plugins: [router, pinia] } })
}

beforeEach(async () => {
  vi.restoreAllMocks()
  await router.push('/permissions')
})

describe('PermissionsView', () => {
  it('loads permissions on mount', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([fakePerm])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('tasks:read')
  })

  it('shows empty state when no permissions', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('No permissions defined')
  })

  it('shows error when loading fails', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockRejectedValue(new Error('Network error'))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Failed to load permissions')
  })

  it('creates a new permission and adds it to the list', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([fakePerm])
    vi.spyOn(permApi.permissionsApi, 'create').mockResolvedValue(fakePerm2)

    const wrapper = mountView()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('tasks:write')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(permApi.permissionsApi.create).toHaveBeenCalledWith({
      name: 'tasks:write',
      description: null,
    })
    expect(wrapper.text()).toContain('tasks:write')
  })

  it('does not create permission when name is empty', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([])
    const createSpy = vi.spyOn(permApi.permissionsApi, 'create').mockResolvedValue(fakePerm)

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error when create fails', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([])
    vi.spyOn(permApi.permissionsApi, 'create').mockRejectedValue(new Error('HTTP 400'))

    const wrapper = mountView()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('tasks:read')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Failed to create permission')
  })

  it('enters edit mode when Edit is clicked', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([fakePerm])
    const wrapper = mountView()
    await flushPromises()

    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Edit')
    await editBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Save')
    expect(wrapper.text()).toContain('Cancel')
  })

  it('saves edit and updates the list', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([fakePerm])
    vi.spyOn(permApi.permissionsApi, 'update').mockResolvedValue({ ...fakePerm, name: 'tasks:updated' })

    const wrapper = mountView()
    await flushPromises()

    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Edit')
    await editBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    const saveBtn = wrapper.findAll('button').find((b) => b.text() === 'Save')
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(permApi.permissionsApi.update).toHaveBeenCalled()
    expect(wrapper.text()).toContain('tasks:updated')
  })

  it('cancels edit when Cancel is clicked', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([fakePerm])
    const wrapper = mountView()
    await flushPromises()

    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Edit')
    await editBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === 'Cancel')
    await cancelBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Edit')
    expect(wrapper.text()).not.toContain('Save')
  })

  it('deletes a permission after confirmation', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([fakePerm])
    vi.spyOn(permApi.permissionsApi, 'delete').mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mountView()
    await flushPromises()

    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === 'Delete')
    await deleteBtn!.trigger('click')
    await flushPromises()

    expect(permApi.permissionsApi.delete).toHaveBeenCalledWith('p1')
    expect(wrapper.text()).not.toContain('tasks:read')
  })

  it('does not delete when confirm is cancelled', async () => {
    vi.spyOn(permApi.permissionsApi, 'list').mockResolvedValue([fakePerm])
    const deleteSpy = vi.spyOn(permApi.permissionsApi, 'delete').mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    const wrapper = mountView()
    await flushPromises()

    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === 'Delete')
    await deleteBtn!.trigger('click')
    await flushPromises()

    expect(deleteSpy).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('tasks:read')
  })
})
