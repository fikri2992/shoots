import { createPinia, setActivePinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import JourneyPage from '@/pages/JourneyPage.vue'
import { useShootsStore } from '@/stores/shoots'

let pinia

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
})

describe('Journey repeatability evidence', () => {
  it('separates recurrence from settled Reproduce evidence', () => {
    const store = useShootsStore()
    store.profile = { shots: 8, keepers: 1, scenes: 3, dimensions: [], blind_spots: [] }
    store.mobile = {}
    store.techniques = [
      {
        technique_id: 'rule_of_thirds',
        name: 'Rule of thirds',
        family: 'composition',
        status: 'recurring',
        sightings: 4,
        corroborated_shots: 3,
        distinct_shoots: 2,
        reproduce_sessions: 0,
      },
      {
        technique_id: 'panning',
        name: 'Panning',
        family: 'exposure',
        status: 'recurring',
        sightings: 6,
        corroborated_shots: 5,
        distinct_shoots: 3,
        reproduce_sessions: 2,
        evaluable_reproduce_sessions: 2,
        criteria_met_sessions: 1,
      },
    ]

    const wrapper = shallowMount(JourneyPage, { global: { plugins: [pinia] } })
    const text = wrapper.text()

    expect(text).toContain('What keeps recurring')
    expect(text).not.toContain('What has become repeatable')
    expect(text).toContain('Recurring does not prove deliberate control')
    expect(text).toContain('2 settled sessions · 2 evaluable · 1 met Criteria')
  })

  it('routes a terminal Experiment draft to its own Keeper source', () => {
    const store = useShootsStore()
    store.profile = { shots: 2, keepers: 1, scenes: 1, dimensions: [], blind_spots: [] }
    store.experiments = [
      {
        id: 'experiment-1',
        type: 'reproduce',
        title: 'Repeat negative space',
        status: 'completed',
        reference_shot_id: 'keeper-1',
        result_shot_ids: ['result-1'],
        verdicts: [],
      },
    ]
    store.shots = [
      { shot: { id: 'keeper-1', kept_at: '2026-08-27T00:00:00Z', blobs: {} }, analysis: null },
    ]
    store.mobile = {
      latest_deconstruction: {
        id: 'draft-1',
        source_type: 'experiment',
        source_id: 'experiment-1',
        source_revision: 1,
        status: 'needs_cover',
        pages: [],
      },
    }

    const wrapper = shallowMount(JourneyPage, { global: { plugins: [pinia] } })

    expect(wrapper.text()).toContain('Share how you worked the Experiment')
    expect(wrapper.text()).toContain('built from this Experiment')
    expect(wrapper.text()).toContain('Create Deconstruction')
  })
})
