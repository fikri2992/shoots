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
import ScoutQuestionStep from './ScoutQuestionStep.vue'
import SeedStep from './SeedStep.vue'
import NowPage from '@/pages/NowPage.vue'
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
    expect(wrapper.text()).toMatch(/Existing files are read only when you select them/i)
    expect(wrapper.text()).toMatch(/Phone Source and direct upload work without Drive/i)
    expect(wrapper.find('button').text()).toBe('Connect optional Drive')
  })
})

describe('NowPage Drive independence', () => {
  it('starts direct upload without requiring the optional Drive folder', () => {
    const store = useShootsStore()
    store.me = { id: 'photographer-1', drive_folder_id: '' }
    store.shots = []
    const wrapper = render(NowPage)

    expect(store.accountReady).toBe(true)
    expect(store.driveConnected).toBe(false)
    expect(wrapper.text()).toContain('Choose a few Shots you already made')
    expect(wrapper.text()).toContain('Drive is optional')
    expect(wrapper.text()).not.toContain('Connect optional Drive')
  })

  it('shows the completed Shoot before an optional Experiment', () => {
    const store = useShootsStore()
    store.me = { id: 'photographer-1', drive_folder_id: '' }
    store.shots = [
      {
        shot: {
          id: 'shot-1',
          filename: 'ridge.jpg',
          blobs: {},
          status: 'analyzed',
          ingested_at: '2026-08-29T06:00:00Z',
        },
        analysis: { techniques: [], critique: 'A distant ridge anchors the frame.' },
      },
    ]
    store.experiment = experiment({ title: 'Try a wider foreground' })
    store.mobile = {
      latest_shoot_record: {
        shoot_id: 'shoot-1',
        revision: 1,
        shot_ids: ['shot-1'],
        run_outcomes: { 'shot-1': 'completed' },
        receipt: {
          summary: 'The distant ridge stayed while the foreground changed.',
          shot_count: 1,
          scene_count: 1,
          repeated: ['The ridge stayed.'],
          varied: ['The foreground changed.'],
        },
        scout: { reason: 'Scout explained the supported pattern.' },
      },
    }

    const wrapper = render(NowPage, {
      global: { mocks: { $route: { query: {} } } },
    })

    expect(wrapper.text()).toContain('Your Shoot is ready')
    expect(wrapper.text()).toContain('After these Shots arrived, Shoots handled the reading')
    expect(wrapper.text()).toContain('Companion receipt')
    expect(wrapper.text()).toContain('Shoots handled')
    expect(wrapper.text()).toContain('You decided')
    expect(wrapper.text()).toContain('The result')
    expect(wrapper.text()).toContain('Next')
    expect(wrapper.text()).toContain('Open optional Experiment')
    expect(wrapper.text()).not.toContain('Try a wider foreground')
  })

  it('shows a saved Direction after the settled Shoot result', () => {
    const store = useShootsStore()
    store.me = { id: 'photographer-1', drive_folder_id: '' }
    store.shots = [
      {
        shot: {
          id: 'market-shot',
          filename: 'market.jpg',
          blobs: { thumb: 'users/u/shots/market/thumb.jpg' },
          status: 'analyzed',
          ingested_at: '2026-08-29T06:00:00Z',
        },
        analysis: { techniques: [], critique: '' },
      },
    ]
    store.mobile = {
      latest_shoot_record: {
        shoot_id: 'shoot-1',
        revision: 1,
        shot_ids: ['market-shot'],
        receipt: { summary: 'One settled Shot.' },
        scout: { reason: 'Scout saved a supported question.' },
      },
      experiment_directions: [
        {
          id: 'direction-1',
          source_shot_id: 'market-shot',
          technique_id: 'leading_lines',
          question: 'Could you use Leading lines deliberately in a different Scene?',
          corroborated_shots: 6,
          distinct_shoots: 3,
          state: 'saved',
        },
      ],
    }

    const wrapper = render(NowPage, {
      global: { mocks: { $route: { query: {} } } },
    })

    expect(wrapper.text()).toContain('Your Shoot is ready')
    expect(wrapper.text()).toContain('Does this question fit today?')
    expect(wrapper.text().indexOf('Your Shoot is ready')).toBeLessThan(
      wrapper.text().indexOf('Does this question fit today?'),
    )
    expect(wrapper.text()).toContain('Try it today')
    expect(wrapper.text()).toContain('Shoot freely')
    expect(wrapper.text()).toContain('Starting fixes the checks before the normal Camera opens')
    expect(wrapper.text()).not.toContain('Your outing became a useful record')
  })

  it('does not present an older Shoot Record as the result of a newer open Shoot', () => {
    const store = useShootsStore()
    store.me = { id: 'photographer-1', drive_folder_id: '' }
    store.shots = [
      {
        shot: {
          id: 'new-shot',
          filename: 'new.jpg',
          status: 'analyzed',
          ingested_at: '2026-08-30T06:00:00Z',
          blobs: {},
        },
        analysis: { techniques: [], critique: 'A real new read.' },
      },
    ]
    store.mobile = {
      latest_shoot: {
        id: 'new-shoot',
        status: 'open',
        revision: 1,
        ordered_shot_ids: ['new-shot'],
        ordered_scene_ids: ['new-scene'],
      },
      latest_shoot_record: {
        shoot_id: 'old-sample-shoot',
        revision: 1,
        shot_ids: ['old-sample-shot'],
        receipt: { shot_count: 10, scene_count: 3 },
        scout: { route: 'explain', reason: 'Old fixture result.' },
      },
    }

    const wrapper = render(NowPage, {
      global: { mocks: { $route: { query: {} } } },
    })

    expect(wrapper.text()).toContain('Shoots is keeping this Shoot together')
    expect(wrapper.text()).toContain('30 minutes')
    expect(wrapper.text()).not.toContain('Your Shoot is ready')
    expect(wrapper.text()).not.toContain('Old fixture result')
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

describe('ScoutQuestionStep', () => {
  it('offers only evidenced choices and records one explicit answer', async () => {
    const store = useShootsStore()
    store.answerScoutQuestion = vi.fn()
    const record = {
      shoot_id: 'shoot-1',
      revision: 2,
      scout: {
        question: {
          prompt: 'Which decision were you exploring in this Shoot?',
          options: [
            { id: 'technique_backlight', label: 'Backlight', technique_id: 'backlight' },
            { id: 'just_shooting', label: 'I was just shooting', technique_id: '' },
          ],
        },
      },
    }
    const wrapper = render(ScoutQuestionStep, { props: { record } })

    expect(wrapper.text()).toContain(record.scout.question.prompt)
    expect(wrapper.text()).toContain('Your answer stays with this Shoot')
    await wrapper.findAll('button')[0].trigger('click')
    expect(store.answerScoutQuestion).toHaveBeenCalledWith('shoot-1', 2, 'technique_backlight')
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
    expect(wrapper.text()).toContain('2 result Shots are here')
    expect(wrapper.text()).not.toContain('It stayed wide.') // behind "What it looked at"
  })
})
