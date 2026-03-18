import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import RolesView from './RolesView.vue'
import * as rolesModule from '../api/roles'
import * as permModule from '../api/permissions'

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/roles', component: RolesView }],
})

const fakePerm = { id: 'p1', name: 'tasks:read', description: null, created_at: '' }
const fakePerm2 = { id: 'p2', name: 'tasks:write', description: null, created_at: '' }
const fakeRole = { id: 'r1', name: 'admin', description: 'Admin role', created_at: '', permissions: [fakePerm] }
const fakeRole2 = { id: 'r2', name: 'viewer', description: null, created_at: '', permissions: [] }

function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(RolesView, { global: { plugins: [router, pinia] } })
}

beforeEach(async () => {
  vi.restoreAllMocks()
  await router.push('/roles')
})

describe('RolesView', () => {
  it('loads roles and permissions on mount', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([fakePerm])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('admin')
    expect(wrapper.text()).toContain('Admin role')
  })

  it('shows error when loading fails', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockRejectedValue(new Error('Network'))
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Impossible de charger les données')
  })

  it('shows empty state when no roles', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Aucun rôle')
  })

  it('creates a new role', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    vi.spyOn(rolesModule.rolesApi, 'create').mockResolvedValue(fakeRole2)

    const wrapper = mountView()
    await flushPromises()

    const inputs = wrapper.findAll('input[type="text"]')
    await inputs[0].setValue('viewer')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(rolesModule.rolesApi.create).toHaveBeenCalledWith({ name: 'viewer', description: null })
    expect(wrapper.text()).toContain('viewer')
  })

  it('does not create role when name is empty', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    const createSpy = vi.spyOn(rolesModule.rolesApi, 'create').mockResolvedValue(fakeRole)

    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(createSpy).not.toHaveBeenCalled()
  })

  it('shows error when create fails', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    vi.spyOn(rolesModule.rolesApi, 'create').mockRejectedValue(new Error('HTTP 409'))

    const wrapper = mountView()
    await flushPromises()

    const inputs = wrapper.findAll('input[type="text"]')
    await inputs[0].setValue('admin')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Impossible de créer le rôle')
  })

  it('enters edit mode when Modifier is clicked', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole2])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Modifier')
    await editBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Sauvegarder')
    expect(wrapper.text()).toContain('Annuler')
  })

  it('saves role edit', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole2])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    vi.spyOn(rolesModule.rolesApi, 'update').mockResolvedValue({ ...fakeRole2, name: 'superviewer' })

    const wrapper = mountView()
    await flushPromises()

    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Modifier')
    await editBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    const saveBtn = wrapper.findAll('button').find((b) => b.text() === 'Sauvegarder')
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(rolesModule.rolesApi.update).toHaveBeenCalled()
    expect(wrapper.text()).toContain('superviewer')
  })

  it('cancels edit when Annuler is clicked', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole2])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    const editBtn = wrapper.findAll('button').find((b) => b.text() === 'Modifier')
    await editBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === 'Annuler')
    await cancelBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Modifier')
    expect(wrapper.text()).not.toContain('Sauvegarder')
  })

  it('deletes a role after confirmation', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole2])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    vi.spyOn(rolesModule.rolesApi, 'delete').mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mountView()
    await flushPromises()

    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === 'Supprimer')
    await deleteBtn!.trigger('click')
    await flushPromises()

    expect(rolesModule.rolesApi.delete).toHaveBeenCalledWith('r2')
    expect(wrapper.text()).not.toContain('viewer')
  })

  it('does not delete when confirm is cancelled', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole2])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([])
    const deleteSpy = vi.spyOn(rolesModule.rolesApi, 'delete').mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    const wrapper = mountView()
    await flushPromises()

    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === 'Supprimer')
    await deleteBtn!.trigger('click')
    await flushPromises()

    expect(deleteSpy).not.toHaveBeenCalled()
  })

  it('shows existing permissions as badges on a role', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([fakePerm, fakePerm2])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('tasks:read')
  })

  it('assigns a permission to a role', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole2])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([fakePerm])
    vi.spyOn(rolesModule.rolesApi, 'assignPermission').mockResolvedValue({ ...fakeRole2, permissions: [fakePerm] })

    const wrapper = mountView()
    await flushPromises()

    const select = wrapper.find('select')
    await select.setValue('p1')
    await select.trigger('change')
    await flushPromises()

    expect(rolesModule.rolesApi.assignPermission).toHaveBeenCalledWith('r2', 'p1')
  })

  it('removes a permission from a role', async () => {
    vi.spyOn(rolesModule.rolesApi, 'list').mockResolvedValue([fakeRole])
    vi.spyOn(permModule.permissionsApi, 'list').mockResolvedValue([fakePerm])
    vi.spyOn(rolesModule.rolesApi, 'removePermission').mockResolvedValue({ ...fakeRole, permissions: [] })

    const wrapper = mountView()
    await flushPromises()

    const badge = wrapper.find('kbd')
    await badge.trigger('click')
    await flushPromises()

    expect(rolesModule.rolesApi.removePermission).toHaveBeenCalledWith('r1', 'p1')
  })
})
