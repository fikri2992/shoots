import { createPinia, setActivePinia } from 'pinia'
import { mount, shallowMount } from '@vue/test-utils'
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

    const wrapper = shallowMount(JourneyPage, {
      global: { plugins: [pinia], stubs: { RouterLink: true } },
    })
    const text = wrapper.text()

    expect(text).toContain('What keeps recurring')
    expect(text).not.toContain('What has become repeatable')
    expect(text).toContain('You have not tried to repeat this on purpose yet')
    expect(text).toContain('1 of 2 checked sessions matched what you set before shooting')
  })

  it('routes a terminal Experiment story to its own marked Shot source', () => {
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

    const wrapper = mount(JourneyPage, {
      global: {
        plugins: [pinia],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })

    const story = wrapper.get('#journey-deconstruction').text()
    expect(story).toContain('This Experiment has an opening, a turn, and an ending')
    expect(story).toContain('You decide which marked Shot opens the story')
    expect(story).toContain('Build my story')
    expect(story).not.toMatch(/Keeper|Deconstruction|Criteria|Verdict|Record/)
  })

  it('opens and downloads every page of a finished visual story', () => {
    const store = useShootsStore()
    store.profile = { shots: 2, keepers: 1, scenes: 1, dimensions: [], blind_spots: [] }
    store.shots = [
      { shot: { id: 'marked-1', kept_at: '2026-08-27T00:00:00Z', blobs: {} }, analysis: null },
    ]
    store.mobile = {
      latest_shoot_record: {
        shoot_id: 'shoot-1',
        revision: 1,
        shot_ids: ['marked-1'],
        receipt: { keeper_shot_ids: ['marked-1'] },
      },
      latest_deconstruction: {
        id: 'story-1',
        source_type: 'shoot',
        source_id: 'shoot-1',
        source_revision: 1,
        status: 'drafted',
        cover_shot_id: 'marked-1',
        suggested_caption: 'One Shoot, kept as one visual story.',
        pages: [
          { title: 'The opening', blob_path: 'users/user-1/story/page-1.jpg' },
          { title: 'The ending', blob_path: 'users/user-1/story/page-2.jpg' },
        ],
      },
    }

    const wrapper = mount(JourneyPage, {
      global: {
        plugins: [pinia],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })

    const story = wrapper.get('#journey-deconstruction')
    expect(story.text()).toContain('The opening')
    expect(story.text()).toContain('The ending')
    expect(story.text()).toContain('Caption for the story')
    expect(story.get('a[download]').attributes('href')).toBe('/api/deconstructions/story-1/download')
    expect(story.get('a[target="_blank"]').attributes('href')).toContain('/api/blobs/')
    expect(story.text()).not.toMatch(/Keeper|Deconstruction|Criteria|Verdict|Record/)
  })

  it('leads a small record with known Evidence and keeps optional Drive separate', async () => {
    const store = useShootsStore()
    store.me = { id: 'photographer-1', drive_folder_id: '' }
    store.profile = {
      shots: 6,
      keepers: 3,
      scenes: 6,
      taste_is_known: false,
      taste_threshold: 5,
      dimensions: [],
      blind_spots: ['Camera height needs more readable EXIF', 'Subject distance needs more Shots'],
    }
    store.mobile = {}
    store.events = [
      {
        id: 'event-1',
        agent: 'analyst',
        stage: 'analyzed',
        detail: { techniques: [] },
        shot_id: '',
        at: '2026-08-29T06:00:00Z',
      },
    ]

    const wrapper = mount(JourneyPage, {
      global: {
        plugins: [pinia],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })

    expect(store.accountReady).toBe(true)
    expect(store.driveConnected).toBe(false)
    expect(wrapper.text()).toContain('Known so far')
    expect(wrapper.text()).toContain('6 readable Shots are in the record')
    expect(wrapper.text()).toContain('3 marked Keepers are direct positive signals')
    expect(wrapper.text()).toContain('Mark a Keeper only when a Shot matters to you')
    expect(wrapper.text()).toContain('3 of 5 marked. After 2 more Shots')
    expect(wrapper.text()).toContain('Next useful signal')
    expect(wrapper.text()).toContain('Keep shooting. If a Shot matters to you, mark it as a Keeper')
    expect(wrapper.text()).toContain('Recent agent activity')
    expect(wrapper.text()).toContain('read it; nothing was clear enough to name')
    const connections = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Phone Source, Drive, and notifications'))
    await connections.trigger('click')
    expect(wrapper.text()).toContain('Connect optional Drive')

    store.me.drive_folder_id = 'drive-folder-1'
    await wrapper.vm.$nextTick()
    expect(store.driveConnected).toBe(true)
    expect(wrapper.text()).not.toContain('Connect optional Drive')
    expect(wrapper.text()).toContain('Check the Drive folder now')
  })

  it('shows the current Experiment without calling a broad distribution a Tendency', () => {
    const store = useShootsStore()
    store.profile = {
      shots: 25,
      keepers: 0,
      scenes: 8,
      taste_is_known: false,
      blind_spots: [],
      dimensions: [
        {
          id: 'key',
          label: 'how bright you keep the frame',
          readable: true,
          narrow: false,
          exploration: 0.63,
          dominant: 'mid key',
          readable_keepers: 0,
          source: 'measurement',
          buckets: [
            { bucket: 'low key', count: 7, keepers: 0 },
            { bucket: 'mid key', count: 13, keepers: 0 },
            { bucket: 'high key', count: 5, keepers: 0 },
          ],
        },
      ],
    }
    store.mobile = {}
    store.experiment = {
      id: 'experiment-1',
      status: 'open',
      title: 'Find the leading line',
      why_now: 'Your current record leaves this direction open.',
    }

    const wrapper = shallowMount(JourneyPage, {
      global: { plugins: [pinia], stubs: { RouterLink: true } },
    })

    expect(wrapper.vm.tendencies).toEqual([])
    expect(wrapper.text()).toContain('Optional next Experiment')
    expect(wrapper.text()).toContain('Find the leading line')
    expect(wrapper.text()).not.toContain('Your strongest readable Tendencies')
  })

  it('keeps a settled Reproduce attempt visible while the Experiment stays open', () => {
    const store = useShootsStore()
    store.profile = {
      shots: 11,
      keepers: 1,
      scenes: 4,
      taste_is_known: false,
      blind_spots: [],
      dimensions: [],
    }
    store.shots = [
      { shot: { id: 'keeper-1', filename: 'keeper.jpg', kept_at: '2026-08-28T00:00:00Z', blobs: {} }, analysis: null },
      { shot: { id: 'result-1', filename: 'result.jpg', blobs: {} }, analysis: null },
    ]
    store.mobile = {}
    store.experiment = {
      id: 'experiment-1',
      type: 'reproduce',
      technique_id: 'layering',
      title: 'Stack three depth layers.',
      status: 'open',
      reference_shot_id: 'keeper-1',
      result_shot_ids: ['result-1'],
      criteria: { text: ['The frame contains three distinct depth zones.'] },
      verdicts: [
        {
          shot_id: 'result-1',
          criteria_met: false,
          feedback: 'Add a distinct foreground anchor before trying again.',
        },
      ],
      issued_at: '2026-08-29T00:00:00Z',
    }

    const wrapper = mount(JourneyPage, {
      global: {
        plugins: [pinia],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    const text = wrapper.text()

    expect(text).toContain('1 result Shot is here. One try is too early to call a lasting Change.')
    expect(text).not.toContain('No explicit Experiment result is available yet.')
    expect(text).toContain('What you were trying to repeat')
    expect(text).toContain('Result 1 · Not yet')
  })

  it('leads with current Keeper facts and hides old prompt-control text', () => {
    const store = useShootsStore()
    store.profile = {
      shots: 25,
      keepers: 5,
      scenes: 8,
      taste_is_known: true,
      blind_spots: [],
      dimensions: [
        {
          id: 'key',
          label: 'how bright you keep the frame',
          readable: true,
          narrow: false,
          exploration: 0.63,
          dominant: 'mid key',
          readable_keepers: 5,
          source: 'measurement',
          buckets: [
            { bucket: 'low key', count: 7, keepers: 1 },
            { bucket: 'mid key', count: 13, keepers: 4 },
            { bucket: 'high key', count: 5, keepers: 0 },
          ],
        },
      ],
    }
    store.mobile = {}
    store.journey = [
      {
        id: 'legacy-update',
        body: 'Your record has enough Shots for a measured update.',
        shots: 25,
        created_at: '2026-08-28T00:00:00Z',
        evidence: [
          '25 Shots read in total.',
          'the photographer has not marked enough keepers to say what they value — do not speak about taste',
        ],
      },
    ]

    const wrapper = shallowMount(JourneyPage, {
      global: { plugins: [pinia], stubs: { RouterLink: true } },
    })

    expect(wrapper.vm.keeperSignals[0]).toMatchObject({ dominant: 'mid key', keepers: 4 })
    expect(wrapper.text()).toContain('What your Keeper marks show')
    expect(wrapper.text()).toContain('4 of 5 readable Keepers')
    expect(wrapper.text()).not.toContain('do not speak about taste')
  })

  it('connects completed work, Photographer choice, every result, and later Scout memory', () => {
    const store = useShootsStore()
    store.profile = {
      shots: 9,
      keepers: 1,
      scenes: 4,
      taste_is_known: false,
      taste_threshold: 5,
      dimensions: [],
      blind_spots: [],
    }
    store.techniques = []
    store.shots = [
      { shot: { id: 'keeper-1', filename: 'keeper.jpg', kept_at: '2026-08-28T00:00:00Z', blobs: {} }, analysis: null },
      { shot: { id: 'result-1', filename: 'result-one.jpg', blobs: {} }, analysis: null },
      { shot: { id: 'result-2', filename: 'result-two.jpg', blobs: {} }, analysis: null },
    ]
    store.experiments = [
      {
        id: 'experiment-1',
        type: 'reproduce',
        technique_id: 'panning',
        title: 'Repeat panning',
        status: 'completed',
        reference_shot_id: 'keeper-1',
        result_shot_ids: ['result-1', 'result-2'],
        criteria: { text: ['The subject stays readable while the background carries directional blur.'] },
        verdicts: [
          {
            shot_id: 'result-1',
            criteria_met: true,
            feedback: 'The subject stayed readable. Next: try it in another Scene.',
          },
        ],
        change: {
          state: 'unchanged',
          outcome: 'The comparable panning distribution stayed unchanged.',
        },
        issued_at: '2026-08-28T00:00:00Z',
        closed_at: '2026-08-29T00:00:00Z',
      },
    ]
    store.mobile = {
      latest_shoot_record: {
        shoot_id: 'shoot-current',
        revision: 1,
        shot_ids: ['keeper-1', 'result-1', 'result-2'],
        receipt: { shot_count: 3, scene_count: 2, summary: 'Panning appeared again.' },
        scout: {
          route: 'explain',
          reason: 'This Shoot has a supported pattern worth showing without prescribing a task.',
          rejected_routes: [
            {
              route: 'reproduce',
              reason: 'Automatic Reproduce was deprioritized after two comparable unchanged outcomes for the available Keeper-backed Technique.',
            },
          ],
        },
      },
      recent_interventions: [
        {
          id: 'intervention-2',
          route: 'reproduce',
          technique_id: 'panning',
          attempt_state: 'completed',
          observable_outcome: 'unchanged',
          result_shot_ids: ['result-1', 'result-2'],
          criteria_met_results: 1,
          abstentions: 1,
          change_state: 'unchanged',
          comparability: 'comparable',
          outcome_reason: 'The comparable panning distribution stayed unchanged.',
          updated_at: '2026-08-29T00:00:00Z',
        },
        {
          id: 'intervention-1',
          route: 'reproduce',
          technique_id: 'panning',
          attempt_state: 'completed',
          observable_outcome: 'unchanged',
          result_shot_ids: ['older-result'],
          criteria_met_results: 0,
          abstentions: 0,
          change_state: 'unchanged',
          comparability: 'comparable',
          outcome_reason: 'The earlier comparable distribution stayed unchanged.',
          updated_at: '2026-08-27T00:00:00Z',
        },
      ],
    }

    const wrapper = mount(JourneyPage, {
      global: {
        plugins: [pinia],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    const text = wrapper.text()

    expect(text).toContain('Your photography loop')
    expect(text).toContain('Shoots read 3 Shots and grouped them into 2 Scenes')
    expect(text).toContain('You completed an Experiment with 2 result Shots')
    expect(text).toContain('2 result Shots · 1 matched every check · 1 could not be checked')
    expect(text).toContain('2 comparable Panning outcomes stayed unchanged')
    expect(text).toContain('Scout did not offer that Technique automatically in this Shoot')
    expect(text).toContain('What you were trying to repeat')
    expect(text).toContain('Result 1 · Matched')
    expect(text).toContain('Result 2 · Could not check')
    expect(text).toContain('This checks one choice you set before shooting. It does not grade the Shot')
  })

  it('keeps a Sample Record visibly read-only without claiming agent work', () => {
    const store = useShootsStore()
    store.me = { id: 'sample-user', record_mode: 'sample', drive_folder_id: 'sample-drive' }
    store.profile = {
      shots: 10,
      keepers: 0,
      scenes: 3,
      taste_is_known: false,
      taste_threshold: 5,
      blind_spots: ['camera height'],
      dimensions: [
        {
          id: 'key',
          label: 'how bright you keep the frame',
          readable: true,
          narrow: true,
          exploration: 0.1,
          dominant: 'mid key',
          readable_keepers: 0,
          source: 'model read',
          buckets: [{ bucket: 'mid key', count: 10, keepers: 0 }],
        },
      ],
    }
    store.techniques = [
      {
        technique_id: 'layering',
        name: 'Foreground, midground, background',
        status: 'recurring',
        corroborated: 10,
        attempts: 10,
        corroborated_shots: 10,
        distinct_shoots: 1,
        reproduce_sessions: 0,
      },
    ]
    store.journey = [{
      id: 'sample-update',
      body: 'Sample story text.',
      shots: 10,
      created_at: '2025-12-06T06:00:00Z',
      evidence: ['Fixture support line.'],
      provenance: { sample_size: 10, model: 'not-a-real-run' },
    }]
    store.mobile = {
      latest_shoot_record: {
        shoot_id: 'sample-shoot',
        revision: 1,
        shot_ids: Array.from({ length: 10 }, (_, index) => `sample-${index + 1}`),
        receipt: { shot_count: 10, scene_count: 3, summary: 'Sample Shoot summary.' },
      },
    }
    store.events = [{ id: 'fixture-event', agent: 'fixture', stage: 'sample', detail: {} }]

    const wrapper = mount(JourneyPage, {
      global: {
        plugins: [pinia],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    const text = wrapper.text()

    expect(text).toContain('Inspect a hand-authored Journey layout')
    expect(text).toContain('No agents ran')
    expect(text).toContain('No ingestion, Analysis, or grouping ran')
    expect(text).toContain('Sample only · no story was built')
    expect(text).toContain('Connections · disabled in sample')
    expect(text).not.toContain('Shoots handled')
    expect(text).not.toContain('Shoots read 10 Shots and grouped them into 3 Scenes')
    expect(text).not.toContain('Mark a Keeper only')
    expect(text).not.toContain('Build my story')
    expect(text).not.toContain('Create pairing code')
    expect(text).not.toContain('Check the Drive folder now')
    expect(text).not.toContain('Recent agent activity')
    expect(text).not.toContain('model read')
    expect(text).not.toContain('You have not tried to repeat this on purpose yet')
  })
})
