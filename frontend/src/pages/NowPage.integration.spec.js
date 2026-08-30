import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import NowPage from '@/pages/NowPage.vue'
import { useShootsStore } from '@/stores/shoots'

const EmptyPage = { template: '<div />' }

function shotView(id, filename) {
  return {
    shot: {
      id,
      filename,
      status: 'analyzed',
      ingested_at: '2026-08-30T06:00:00Z',
      blobs: { thumb: `users/photographer/shots/${id}/thumb.jpg` },
    },
    analysis: { techniques: [], critique: '' },
  }
}

describe('Now Scout Recommendation integration', () => {
  it('shows the finished Shoot before one evidence-backed idea and keeps alternatives one tap away', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'now', component: NowPage },
        { path: '/shots/:shotId', name: 'shot', component: EmptyPage },
        { path: '/shoots/:shootId/records/:revision', name: 'shoot-record', component: EmptyPage },
      ],
    })
    await router.push('/')
    await router.isReady()

    const store = useShootsStore()
    store.me = { id: 'photographer', drive_folder_id: '' }
    store.shots = [
      shotView('shot-centre', 'cabin.jpg'),
      shotView('shot-depth', 'garden.jpg'),
      shotView('shot-horizon', 'mountain.jpg'),
    ]
    store.mobile = {
      recent_scout_answers: [],
      latest_shoot: {
        id: 'shoot-1',
        status: 'settled',
        revision: 1,
        current_record_revision: 1,
        ordered_shot_ids: ['shot-centre', 'shot-depth', 'shot-horizon'],
      },
      latest_shoot_record: {
        shoot_id: 'shoot-1',
        revision: 1,
        shot_ids: ['shot-centre', 'shot-depth', 'shot-horizon'],
        receipt: { shot_count: 3, scene_count: 1 },
        scout: {
          route: 'ask',
          warrant: [
            { technique_id: 'deep_dof', shot_ids: ['shot-depth'] },
            { technique_id: 'horizon_placement', shot_ids: ['shot-horizon'] },
            { technique_id: 'centre_composition', shot_ids: ['shot-centre'] },
          ],
          question: {
            id: 'question-1',
            prompt: 'What were you paying attention to in this Shoot?',
            options: [
              { id: 'technique_centre_composition', label: 'Deliberate centre', technique_id: 'centre_composition' },
              { id: 'technique_deep_dof', label: 'Deep depth of field', technique_id: 'deep_dof' },
              { id: 'technique_horizon_placement', label: 'Horizon placement', technique_id: 'horizon_placement' },
              { id: 'just_shooting', label: 'I was just shooting', technique_id: '' },
            ],
          },
        },
      },
    }

    const wrapper = mount(NowPage, { global: { plugins: [pinia, router] } })

    expect(wrapper.text()).toContain('Your Shoot is ready')
    expect(wrapper.text()).toContain('Open Shoot Record')
    expect(wrapper.text()).toContain('One idea for your next outing')
    expect(wrapper.text().indexOf('Your Shoot is ready')).toBeLessThan(
      wrapper.text().indexOf('One idea for your next outing'),
    )
    expect(wrapper.text()).toContain('Try Deliberate centre on purpose')
    expect(wrapper.text()).toContain('This is a recommendation, not a claim about what you intended')
    expect(wrapper.findAll('img')).toHaveLength(4)
    expect(wrapper.get('button[data-recommendation-action="accept"]').text()).toBe('Try this Experiment')
    expect(wrapper.find('[data-recommendation-action="just-shooting"]').exists()).toBe(false)
    await wrapper.get('button[data-recommendation-action="another"]').trigger('click')
    expect(wrapper.text()).toContain('Try Deep depth of field on purpose')
    expect(wrapper.get('a[href="/shots/shot-depth?from=now"]').exists()).toBe(true)
  })
})
