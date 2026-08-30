import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it } from 'vitest'

import ShotCanvas from '@/components/ShotCanvas.vue'
import ShotPage from '@/pages/ShotPage.vue'
import { useShootsStore } from '@/stores/shoots'

let pinia
let router

beforeEach(async () => {
  pinia = createPinia()
  setActivePinia(pinia)
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/shots', name: 'shots', component: { template: '<div />' } },
      { path: '/shots/:shotId', name: 'shot', component: ShotPage, props: true },
      { path: '/', name: 'now', component: { template: '<div />' } },
    ],
  })
  await router.push('/shots/teaching-shot')
  await router.isReady()
})

describe('ShotPage teaching receipt', () => {
  it('keeps one read together and opens with its matching image layer', async () => {
    const store = useShootsStore()
    store.shots = [
      {
        shot: {
          id: 'teaching-shot',
          filename: 'IMG_teaching.jpg',
          status: 'analyzed',
          blobs: {
            original: 'users/u/shots/teaching/original.jpg',
            finding_marked: 'users/u/shots/teaching/finding.jpg',
          },
          grid: { cols: 8, rows: 6, width: 800, height: 600 },
          exif: {},
        },
        analysis: {
          shot_id: 'teaching-shot',
          model: 'gemini-test',
          prompt_version: 'prompt-test',
          techniques: [],
          observations: [],
          findings: [
            {
              finding_id: 'off_guide_subject',
              what: 'The subject misses the selected placement line.',
              why: 'Its centre is 18% of frame width from the nearest line.',
              cells: ['B3', 'C3'],
            },
          ],
          composition: {
            guide: 'thirds',
            subject_cells: ['B3', 'C3'],
            moves: [],
          },
          critique: 'The complete model read stays behind disclosure.',
          panel: {},
        },
        teaching: {
          keep_title: 'Negative space',
          keep_proof: 'Two independent Analyst lenses agreed.',
          keep_authority: 'model_read',
          keep_technique_id: 'negative_space',
          keep_mark: { kind: 'region', cells: ['B3', 'C3'] },
          notice_title: 'The subject misses the selected placement line.',
          notice_proof: 'Its centre is 18% of frame width from the nearest line.',
          notice_finding_id: 'off_guide_subject',
          notice_authority: 'measured',
          notice_mark: {
            kind: 'finding',
            cells: ['B3', 'C3'],
            finding_id: 'off_guide_subject',
          },
          try_text: 'Move the subject toward the right third.',
          try_reason: 'Keep the open area while making the landing point deliberate.',
          try_kind: 'move',
          try_mark: {
            kind: 'move',
            cells: ['B3', 'C3'],
            to_cells: ['F3', 'G3'],
          },
          visible_check: 'Check that the subject meets the selected guide.',
          check_mark: {
            kind: 'move',
            cells: ['B3', 'C3'],
            to_cells: ['F3', 'G3'],
          },
          primary_layer: 'finding',
          guide: 'thirds',
        },
      },
    ]

    const wrapper = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      global: { plugins: [pinia, router] },
    })

    const canvas = wrapper.findComponent(ShotCanvas)
    expect(wrapper.text()).toContain('A closer look')
    expect(wrapper.text()).toContain('1 of 4')
    expect(wrapper.text()).toContain('Negative space')
    expect(wrapper.text()).not.toContain('Ask about this Shot')
    expect(canvas.props('mark').kind).toBe('region')
    expect(canvas.props('src')).toContain('/original.jpg')

    await wrapper.findAll('button').find((button) => button.text() === 'Next').trigger('click')
    expect(wrapper.text()).toContain('WHAT THE CAMERA FOUND')
    expect(canvas.props('mark').kind).toBe('finding')
    expect(canvas.props('src')).toContain('/finding.jpg')

    await wrapper.findAll('button').find((button) => button.text() === 'Next').trigger('click')
    expect(wrapper.text()).toContain('TRY THIS')
    expect(canvas.props('mark').kind).toBe('move')

    await wrapper.findAll('button').find((button) => button.text() === 'Next').trigger('click')
    expect(wrapper.text()).toContain('CHECK NEXT TIME')
    expect(canvas.props('mark').kind).toBe('move')

    const thirds = wrapper.findAll('button').find((button) => button.text() === 'thirds')
    await thirds.trigger('click')
    expect(canvas.props('layer')).toBe('guide')
    expect(canvas.props('mark')).toBe(null)
    expect(canvas.props('src')).toContain('/original.jpg')
  })

  it('draws leading lines only from a rendered artifact', async () => {
    const store = useShootsStore()
    const base = {
      shot: {
        id: 'path-shot',
        filename: 'market.jpg',
        status: 'analyzed',
        blobs: { original: 'users/u/shots/path/original.jpg' },
        grid: { cols: 7, rows: 9, width: 700, height: 900 },
        exif: {},
      },
      analysis: {
        shot_id: 'path-shot',
        techniques: [],
        observations: [],
        findings: [],
        composition: { subject_cells: ['D3', 'E3'], moves: [] },
        panel: {},
      },
      teaching: {
        keep_title: 'Leading lines',
        keep_proof: 'Two pavement boundaries lead toward the subject.',
        keep_technique_id: 'leading_lines',
          keep_mark: {
            kind: 'line',
            cells: ['D9', 'D7', 'D5', 'G9', 'F7', 'E5'],
            technique_id: 'leading_lines',
            paths: [
            { points: ['D9', 'D7', 'D5'], leads_to: ['D4', 'E4'] },
            { points: ['G9', 'F7', 'E5'], leads_to: ['D4', 'E4'] },
          ],
        },
      },
    }
    store.shots = [base]
    const unverified = mount(ShotPage, {
      props: { shotId: 'path-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(unverified.text()).not.toContain('Leading lines')
    expect(unverified.text()).toContain('Start with what catches your eye first.')
    expect(unverified.find('[data-story-line]').exists()).toBe(false)
    unverified.unmount()

    store.shots = [
      {
        ...base,
        teaching: {
          ...base.teaching,
          keep_mark: {
            ...base.teaching.keep_mark,
            technique_id: 'leading_lines',
            visual_artifact: {
              kind: 'verified_paths',
              authority: 'located_model_read',
              status: 'rendered',
              verification: 'bounded',
              label: 'Edge-checked visual path',
              legend: 'The path follows visible edges; the Technique name remains a visual read.',
              blob_path: 'users/u/shots/path/visual-evidence/leading-lines.jpg',
              metrics: { path_count: 2 },
            },
          },
        },
      },
    ]
    const verified = mount(ShotPage, {
      props: { shotId: 'path-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(verified.text()).toContain('Leading lines')
    expect(verified.text()).toContain("Shoots' visual read")
    expect(verified.findComponent(ShotCanvas).props('src')).toContain('leading-lines.jpg')
    expect(verified.find('[data-story-line]').exists()).toBe(false)
    verified.unmount()

    store.shots = [
      {
        ...base,
        teaching: {
          ...base.teaching,
          keep_mark: {
            kind: 'line',
            cells: ['D6', 'E6', 'F6', 'D7', 'E7', 'F7', 'D8', 'E8', 'F8'],
            paths: [],
          },
        },
      },
    ]
    const legacy = mount(ShotPage, {
      props: { shotId: 'path-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(legacy.text()).not.toContain('Leading lines')
    expect(legacy.text()).toContain('Start with what catches your eye first.')
    expect(legacy.find('[data-story-line]').exists()).toBe(false)
    legacy.unmount()

    store.shots = [
      {
        ...base,
        teaching: {
          ...base.teaching,
          keep_mark: {
            kind: 'line',
            cells: ['D9', 'D7', 'D5'],
            paths: [],
            technique_id: 'leading_lines',
          },
        },
      },
    ]
    const untargeted = mount(ShotPage, {
      props: { shotId: 'path-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(untargeted.text()).not.toContain('Leading lines')
    expect(untargeted.text()).toContain('Start with what catches your eye first.')
    expect(untargeted.find('[data-story-line]').exists()).toBe(false)
  })

  it('requires a rendered artifact before narrating foreground, midground, and background', () => {
    const store = useShootsStore()
    const base = {
      shot: {
        id: 'teaching-shot',
        filename: 'ridge.jpg',
        status: 'analyzed',
        blobs: { original: 'users/u/shots/ridge/original.jpg' },
        grid: { cols: 8, rows: 6, width: 800, height: 600 },
        exif: {},
      },
      analysis: {
        shot_id: 'teaching-shot',
        techniques: [],
        observations: ['The ridge sits beyond a bank of cloud.'],
        findings: [],
        composition: { subject_cells: ['D4', 'E4'], moves: [] },
        panel: {},
      },
      teaching: {
        keep_title: 'Foreground, midground, background',
        keep_proof: 'Foreground, cloud, and ridge form three depth planes.',
        keep_technique_id: 'layering',
        keep_mark: {
          kind: 'region',
          technique_id: 'layering',
          cells: ['B3', 'D3', 'F3', 'B5', 'D5', 'F5'],
          regions: [],
        },
      },
    }
    store.shots = [base]

    const unsupported = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(unsupported.text()).not.toContain('Foreground, midground, background')
    expect(unsupported.text()).toContain('Start with what catches your eye first.')
    expect(unsupported.findAll('[data-story-region]')).toHaveLength(1)
    unsupported.unmount()

    store.shots = [
      {
        ...base,
        teaching: {
          ...base.teaching,
          keep_mark: {
            kind: 'planes',
            technique_id: 'layering',
            cells: ['A6', 'D5', 'D3'],
            regions: [
              { cells: ['A6', 'B6', 'C6', 'D6'], role: 'foreground', order: 0 },
              { cells: ['C5', 'D5', 'E5', 'F5'], role: 'midground', order: 1 },
              { cells: ['C3', 'D3', 'E3', 'F3'], role: 'background', order: 2 },
            ],
          },
        },
      },
    ]
    const regionsOnly = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(regionsOnly.text()).not.toContain('Foreground, midground, background')
    regionsOnly.unmount()

    store.shots[0].teaching.keep_mark.visual_artifact = {
      kind: 'geometry',
      authority: 'relational_model_read',
      status: 'rendered',
      verification: 'bounded',
      label: 'Checked depth regions',
      legend: 'The regions are a checked visual read, not a depth measurement.',
      blob_path: 'users/u/shots/ridge/visual-evidence/layering.jpg',
      metrics: { region_count: 3 },
    }
    const supported = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(supported.text()).toContain('Foreground, midground, background')
    expect(supported.findComponent(ShotCanvas).props('src')).toContain('layering.jpg')
    expect(supported.findAll('[data-story-region]')).toHaveLength(0)
  })

  it('uses an EXIF receipt as proof without drawing unrelated geometry', () => {
    const store = useShootsStore()
    store.shots = [
      {
        shot: {
          id: 'teaching-shot',
          filename: 'wide.jpg',
          status: 'analyzed',
          blobs: { original: 'users/u/shots/wide/original.jpg' },
          grid: { cols: 8, rows: 6, width: 800, height: 600 },
          exif: {},
        },
        analysis: {
          shot_id: 'teaching-shot',
          techniques: [],
          observations: [],
          findings: [],
          composition: {
            subject_cells: ['D4', 'E4'],
            moves: [
              {
                kind: 'move',
                what: 'Move upward.',
                from_cells: ['D4'],
                to_cells: ['D2'],
              },
            ],
          },
          panel: {},
        },
        teaching: {
          keep_title: 'Wide-angle drama',
          keep_proof: 'The camera recorded a 15 mm equivalent focal length.',
          keep_technique_id: 'wide_angle',
          keep_mark: {
            kind: 'line',
            cells: ['A6', 'B6', 'H6'],
            visual_artifact: {
              kind: 'exif_receipt',
              authority: 'measured',
              status: 'rendered',
              label: 'Camera receipt',
              metrics: { focal_mm: 15 },
              blob_path: '',
            },
          },
        },
      },
    ]
    const wrapper = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      global: { plugins: [pinia, router] },
    })
    const canvas = wrapper.findComponent(ShotCanvas)
    expect(wrapper.text()).toContain('Camera receipt')
    expect(wrapper.text()).toContain('focal mm 15')
    expect(canvas.props('layer')).toBe('clean')
    expect(canvas.props('mark')).toBe(null)
    expect(wrapper.find('[data-story-line]').exists()).toBe(false)
    expect(wrapper.find('[data-story-move]').exists()).toBe(false)
  })

  it('turns Keeper-backed Technique Evidence into a saved question, not an Experiment', async () => {
    const store = useShootsStore()
    store.shots = [
      {
        shot: {
          id: 'teaching-shot',
          filename: 'market.jpg',
          status: 'analyzed',
          blobs: { original: 'users/u/shots/market/original.jpg' },
          grid: { cols: 7, rows: 9, width: 700, height: 900 },
          exif: {},
        },
        analysis: {
          shot_id: 'teaching-shot',
          techniques: [],
          observations: [],
          findings: [],
          composition: { subject_cells: ['D4', 'E4'], moves: [] },
          panel: {},
        },
        teaching: {
          keep_title: 'Leading lines',
          keep_proof: 'Two corridor edges converge toward the subject.',
          keep_technique_id: 'leading_lines',
          keep_mark: {
            kind: 'line',
            cells: ['D9', 'D7', 'D5', 'G9', 'F7', 'E5'],
            technique_id: 'leading_lines',
            paths: [
              { points: ['D9', 'D7', 'D5'], leads_to: ['D4', 'E4'] },
              { points: ['G9', 'F7', 'E5'], leads_to: ['D4', 'E4'] },
            ],
            visual_artifact: {
              kind: 'verified_paths',
              authority: 'located_model_read',
              status: 'rendered',
              verification: 'bounded',
              label: 'Edge-checked visual path',
              blob_path: 'users/u/shots/path/visual-evidence/leading-lines.jpg',
              metrics: { path_count: 2 },
            },
          },
        },
        technique_context: {
          leading_lines: {
            technique_id: 'leading_lines',
            status: 'recurring',
            corroborated_shots: 6,
            distinct_scenes: 4,
            distinct_shoots: 3,
            reproduce_sessions: 0,
            evaluable_reproduce_sessions: 0,
            criteria_met_sessions: 0,
            positive_keeper_shots: 2,
          },
        },
      },
    ]
    store.mobile = { experiment_directions: [] }

    const wrapper = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      global: { plugins: [pinia, router] },
    })

    expect(wrapper.text()).toContain('Shoots has seen this clearly in 6 Shots from 3 Shoots')
    expect(wrapper.text()).toContain('2 Keepers are part of that')
    expect(wrapper.text()).toContain('You have not tried to repeat this on purpose yet')
    expect(wrapper.text()).toContain('Want to try this same choice in a different Scene?')
    expect(wrapper.text()).toContain('Try another day')
    expect(wrapper.text()).toContain('Leave it')
    expect(store.experiment).toBe(null)

    store.mobile = {
      experiment_directions: [
        {
          id: 'direction-1',
          source_shot_id: 'teaching-shot',
          technique_id: 'leading_lines',
          question: 'Could you use Leading lines deliberately in a different Scene?',
          state: 'saved',
        },
      ],
    }
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Saved for another day')
    expect(wrapper.text()).toContain('Nothing has started yet')
    expect(wrapper.text()).toContain('Delete saved question')
    expect(wrapper.text()).not.toContain('Try another day')
  })

  it('opens a large tested-crop comparison with one slider control', async () => {
    const store = useShootsStore()
    store.shots = [
      {
        shot: {
          id: 'teaching-shot',
          filename: 'crop-test.jpg',
          status: 'analyzed',
          blobs: {
            original: 'users/u/shots/crop-test/original.jpg',
            crop: 'users/u/shots/crop-test/crop.jpg',
          },
          grid: { cols: 8, rows: 6, width: 800, height: 600 },
          exif: {},
        },
        analysis: {
          shot_id: 'teaching-shot',
          techniques: [],
          observations: [],
          findings: [],
          composition: {
            subject_cells: ['D3', 'E3'],
            moves: [
              {
                kind: 'crop',
                what: 'Remove the empty left edge.',
                to_cells: ['B1', 'H6'],
              },
            ],
            suggested_crop_cells: ['B1', 'H6'],
            crop_tested: true,
            crop_reason: 'The tighter frame keeps the subject relationship while removing an empty edge.',
          },
          panel: {},
        },
        teaching: {},
      },
    ]

    const wrapper = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      attachTo: document.body,
      global: { plugins: [pinia, router] },
    })

    const cropDisclosure = wrapper.findAll('button').find((button) => button.text().includes('A crop it tested'))
    await cropDisclosure.trigger('click')
    const preview = wrapper.find('[data-tested-crop-preview]')
    expect(preview.exists()).toBe(true)
    await preview.trigger('click')

    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    expect(document.body.style.overflow).toBe('hidden')
    expect(wrapper.find('[data-crop-comparison-stage]').exists()).toBe(true)
    expect(wrapper.get('img[alt="Original Shot"]').attributes('src')).toContain('/original.jpg')
    expect(wrapper.get('img[alt="Tested crop"]').attributes('src')).toContain('/crop.jpg')
    expect(wrapper.text()).not.toContain('Flicker')
    expect(wrapper.find('[aria-label="Comparison mode"]').exists()).toBe(false)
    const slider = wrapper.get('input[aria-label="Before and after position"]')
    await slider.setValue(72)
    expect(wrapper.find('[data-crop-comparison-stage] span[style]').attributes('style')).toContain('72%')

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(document.body.style.overflow).not.toBe('hidden')
    wrapper.unmount()
  })
})
