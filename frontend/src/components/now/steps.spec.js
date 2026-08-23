/**
 * The Now screen's states. The first two are only ever seen by a brand-new
 * account, so they are checked here rather than by hand.
 */
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ConnectStep from './ConnectStep.vue'
import QuestHero from './QuestHero.vue'
import ReadingStep from './ReadingStep.vue'
import SeedStep from './SeedStep.vue'
import { useShootsStore } from '@/stores/shoots'

const stubs = { RouterLink: { template: '<a><slot /></a>' } }

function quest(extra = {}) {
  return {
    id: 'quest_1',
    technique_id: 'fill_the_frame',
    title: 'Fill the entire frame.',
    brief: '1. Step closer.\n2. Check the edges.',
    why_now: 'Your last frames had clutter at the edges.',
    criteria: { exif: {}, text: ['The subject fills the frame.'] },
    references: [],
    verdicts: [],
    status: 'open',
    issued_at: new Date().toISOString(),
    timing: { light: 'any', reason: 'Any light works for this one.', anchor: '', anchor_at: null },
    reference_clip: '',
    ...extra,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('ConnectStep', () => {
  it('says what connecting does before asking for it', () => {
    const wrapper = mount(ConnectStep)
    expect(wrapper.text()).toMatch(/folder in your Google Drive/i)
    expect(wrapper.find('button').text()).toBe('Connect Drive')
  })
})

describe('SeedStep', () => {
  it('hands every chosen file to the store in one go', async () => {
    const store = useShootsStore()
    store.seed = vi.fn()
    const wrapper = mount(SeedStep)
    const files = [new File(['a'], 'a.jpg'), new File(['b'], 'b.jpg')]

    Object.defineProperty(wrapper.find('input[type=file]').element, 'files', { value: files })
    await wrapper.find('input[type=file]').trigger('change')

    expect(store.seed).toHaveBeenCalledWith(files)
  })

  it('counts the uploads while they run', () => {
    const store = useShootsStore()
    store.seeding = { done: 1, total: 3, name: 'b.jpg' }
    const wrapper = mount(SeedStep)
    expect(wrapper.text()).toContain('Uploading 2 of 3')
    expect(wrapper.find('input[type=file]').exists()).toBe(false)
  })
})

describe('ReadingStep', () => {
  const shot = { shot: { id: 's1', blobs: {}, ingested_at: new Date().toISOString() }, analysis: null }

  it('marks the stages the frame has cleared and lights the next one', () => {
    const store = useShootsStore()
    store.events = [
      { id: 'e2', agent: 'ingest', stage: 'ingested', shot_id: 's1', at: '', detail: {} },
      { id: 'e1', agent: 'ingest', stage: 'queued', shot_id: 's1', at: '', detail: {} },
    ]
    const rows = mount(ReadingStep, { props: { shots: [shot] } }).vm.rows

    expect(rows.map((r) => r.complete)).toEqual([true, true, false])
    expect(rows.find((r) => r.active).key).toBe('analyst.analyzed')
  })

  it('ignores stages belonging to another frame', () => {
    const store = useShootsStore()
    store.events = [{ id: 'e1', agent: 'ingest', stage: 'ingested', shot_id: 'other', at: '', detail: {} }]
    const rows = mount(ReadingStep, { props: { shots: [shot] } }).vm.rows
    expect(rows.every((r) => !r.complete)).toBe(true)
  })
})

describe('QuestHero', () => {
  it('leads with the criteria and keeps the steps behind a disclosure', () => {
    const wrapper = mount(QuestHero, { props: { quest: quest() }, global: { stubs } })
    expect(wrapper.text()).toContain('The subject fills the frame.')
    expect(wrapper.text()).not.toContain('Step closer.')
    expect(wrapper.text()).toContain('How to shoot it')
  })

  it('only promises a clip while the Director could still be rendering one', () => {
    const fresh = mount(QuestHero, { props: { quest: quest() }, global: { stubs } })
    expect(fresh.text()).toContain('rendering a reference clip')

    const old = mount(QuestHero, {
      props: { quest: quest({ issued_at: new Date(Date.now() - 3600_000).toISOString() }) },
      global: { stubs },
    })
    expect(old.text()).not.toContain('rendering a reference clip')
  })

  it('shows the newest attempt, action first', () => {
    const verdicts = [
      { shot_id: 's1', passed: false, feedback: 'Old one. Next: old action.', compared_with: '' },
      { shot_id: 's2', passed: false, feedback: 'It stayed wide. Next: step closer.', compared_with: '' },
    ]
    const wrapper = mount(QuestHero, { props: { quest: quest({ verdicts }) }, global: { stubs } })
    expect(wrapper.text()).toContain('step closer.')
    expect(wrapper.text()).toContain('2 attempts so far')
    expect(wrapper.text()).not.toContain('It stayed wide.') // behind "What it looked at"
  })
})
