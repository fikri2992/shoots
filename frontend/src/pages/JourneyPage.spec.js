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
})
