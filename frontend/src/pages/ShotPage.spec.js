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
          notice_title: 'The subject misses the selected placement line.',
          notice_proof: 'Its centre is 18% of frame width from the nearest line.',
          notice_finding_id: 'off_guide_subject',
          notice_authority: 'measured',
          try_text: 'Move the subject toward the right third.',
          try_reason: 'Keep the open area while making the landing point deliberate.',
          try_kind: 'move',
          visible_check: 'Check that the subject meets the selected guide.',
          primary_layer: 'finding',
          guide: 'thirds',
        },
      },
    ]

    const wrapper = mount(ShotPage, {
      props: { shotId: 'teaching-shot' },
      global: { plugins: [pinia, router] },
    })

    expect(wrapper.text()).toContain('This Shot · one read')
    expect(wrapper.text()).toContain('Keep · model read')
    expect(wrapper.text()).toContain('Notice · measured')
    expect(wrapper.text()).toContain('Try next')
    expect(wrapper.text()).toContain('Check on the next Shot')
    expect(wrapper.text()).not.toContain('What held')
    expect(wrapper.text()).not.toContain('One move to try')

    const canvas = wrapper.findComponent(ShotCanvas)
    expect(canvas.props('layer')).toBe('finding')
    expect(canvas.props('src')).toContain('/finding.jpg')

    const thirds = wrapper.findAll('button').find((button) => button.text() === 'thirds')
    await thirds.trigger('click')
    expect(canvas.props('layer')).toBe('guide')
    expect(canvas.props('src')).toContain('/original.jpg')
  })
})
