/**
 * The Now screen's states. The first two are only ever seen by a brand-new
 * account, so they are checked here rather than by hand.
 */
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ConnectStep from './ConnectStep.vue'
import ExperimentHero from './ExperimentHero.vue'
import ReadingStep from './ReadingStep.vue'
import SeedStep from './SeedStep.vue'
import { useShootsStore } from '@/stores/shoots'

const stubs = { RouterLink: { template: '<a><slot /></a>' } }
let pinia

function render(component, options = {}) {
  return mount(component, {
    ...options,
    global: {
      ...options.global,
      plugins: [pinia],
      stubs: { ...stubs, ...(options.global?.stubs || {}) },
    },
  })
}

function experiment(extra = {}) {
  return {
    id: 'experiment_1',
    type: 'reproduce',
    technique_id: 'fill_the_frame',
    reference_shot_id: 'keeper_1',
    result_shot_ids: [],
    title: 'Fill the entire frame.',
    brief: '1. Step closer.\n2. Check the edges.',
    why_now: 'Your last Shots had clutter at the edges.',
    criteria: { exif: {}, text: ['The subject fills the frame.'] },
    references: [],
    verdicts: [],
    status: 'open',
    issued_at: new Date().toISOString(),
    timing: { light: 'any', reason: 'Any light works for this one.', anchor: '', anchor_at: null },
    ...extra,
  }
}

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
})

describe('ConnectStep', () => {
  it('says what connecting does before asking for it', () => {
    const wrapper = render(ConnectStep)
    expect(wrapper.text()).toMatch(/folder named Shoots/i)
    expect(wrapper.text()).toMatch(/No access to the rest of your Drive/i)
    expect(wrapper.text()).toMatch(/Phone Source and direct upload work without Drive/i)
    expect(wrapper.find('button').text()).toBe('Connect optional Drive')
  })
})

describe('SeedStep', () => {
  it('hands every chosen file to the store in one go', async () => {
    const store = useShootsStore()
    store.seed = vi.fn()
    const wrapper = render(SeedStep)
    const files = [new File(['a'], 'a.jpg'), new File(['b'], 'b.jpg')]

    Object.defineProperty(wrapper.find('input[type=file]').element, 'files', { value: files })
    await wrapper.find('input[type=file]').trigger('change')

    expect(store.seed).toHaveBeenCalledWith(files)
  })

  it('counts the uploads while they run', () => {
    const store = useShootsStore()
    store.seeding = { done: 1, total: 3, name: 'b.jpg' }
    const wrapper = render(SeedStep)
    expect(wrapper.text()).toContain('Uploading 2 of 3')
    expect(wrapper.find('input[type=file]').exists()).toBe(false)
  })
})

describe('ReadingStep', () => {
  const shot = { shot: { id: 's1', blobs: {}, ingested_at: new Date().toISOString() }, analysis: null }

  it('marks the stages the Shot has cleared and lights the next one', () => {
    const store = useShootsStore()
    store.events = [
      { id: 'e2', agent: 'ingest', stage: 'ingested', shot_id: 's1', at: '', detail: {} },
      { id: 'e1', agent: 'ingest', stage: 'queued', shot_id: 's1', at: '', detail: {} },
    ]
    const rows = render(ReadingStep, { props: { shots: [shot] } }).vm.rows

    expect(rows.map((r) => r.complete)).toEqual([true, true, false])
    expect(rows.find((r) => r.active).key).toBe('analyst.analyzed')
  })

  it('ignores stages belonging to another Shot', () => {
    const store = useShootsStore()
    store.events = [{ id: 'e1', agent: 'ingest', stage: 'ingested', shot_id: 'other', at: '', detail: {} }]
    const rows = render(ReadingStep, { props: { shots: [shot] } }).vm.rows
    expect(rows.every((r) => !r.complete)).toBe(true)
  })
})

describe('ExperimentHero', () => {
  it('leads with Criteria and one move, then keeps the full approach behind disclosure', async () => {
    const wrapper = render(ExperimentHero, { props: { experiment: experiment() } })
    expect(wrapper.text()).toContain('The subject fills the frame.')
    expect(wrapper.text()).toContain('Step closer.')
    expect(wrapper.text()).not.toContain('Check the edges.')
    const disclosure = wrapper.findAll('button').find((button) => button.text().includes('The full approach'))
    await disclosure.trigger('click')
    expect(wrapper.text()).toContain('Check the edges.')
  })

  it('shows the newest attempt, action first', () => {
    const verdicts = [
      { shot_id: 's1', criteria_met: false, feedback: 'Old one. Next: old action.', compared_with: '' },
      { shot_id: 's2', criteria_met: false, feedback: 'It stayed wide. Next: step closer.', compared_with: '' },
    ]
    const wrapper = render(ExperimentHero, {
      props: { experiment: experiment({ verdicts, result_shot_ids: ['s1', 's2'] }) },
    })
    expect(wrapper.text()).toContain('step closer.')
    expect(wrapper.text()).toContain('2 explicit result Shots recorded')
    expect(wrapper.text()).not.toContain('It stayed wide.') // behind "What it looked at"
  })
})
