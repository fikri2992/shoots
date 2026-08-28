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
    expect(wrapper.text()).toContain('Visual story')
    expect(wrapper.text()).toContain('1 of 4')
    expect(wrapper.text()).toContain('Negative space')
    expect(canvas.props('mark').kind).toBe('region')
    expect(canvas.props('src')).toContain('/original.jpg')

    await wrapper.findAll('button').find((button) => button.text() === 'Next').trigger('click')
    expect(wrapper.text()).toContain('WHAT SHOOTS MEASURED')
    expect(canvas.props('mark').kind).toBe('finding')
    expect(canvas.props('src')).toContain('/finding.jpg')

    await wrapper.findAll('button').find((button) => button.text() === 'Next').trigger('click')
    expect(wrapper.text()).toContain('WHAT TO CHANGE')
    expect(canvas.props('mark').kind).toBe('move')

    await wrapper.findAll('button').find((button) => button.text() === 'Next').trigger('click')
    expect(wrapper.text()).toContain('CHECK THE NEXT SHOT')
    expect(canvas.props('mark').kind).toBe('move')

    const thirds = wrapper.findAll('button').find((button) => button.text() === 'thirds')
    await thirds.trigger('click')
    expect(canvas.props('layer')).toBe('guide')
    expect(canvas.props('mark')).toBe(null)
    expect(canvas.props('src')).toContain('/original.jpg')
  })

  it('draws explicit leading paths and refuses a broad legacy cell cloud', async () => {
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
          paths: [
            { points: ['D9', 'D7', 'D5'], leads_to: ['D4', 'E4'] },
            { points: ['G9', 'F7', 'E5'], leads_to: ['D4', 'E4'] },
          ],
        },
      },
    }
    store.shots = [base]
    const located = mount(ShotPage, {
      props: { shotId: 'path-shot' },
      global: { plugins: [pinia, router] },
    })
    expect(located.text()).toContain('Leading lines')
    expect(located.findAll('[data-story-line]')).toHaveLength(2)
    located.unmount()

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
    expect(legacy.text()).toContain('Start with the main subject.')
    expect(legacy.find('[data-story-line]').exists()).toBe(false)
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
})
