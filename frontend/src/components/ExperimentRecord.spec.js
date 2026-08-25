/**
 * The Experiment Record as a photographer reads it.
 *
 * The record is the checkable artifact the loop leaves behind, so what matters
 * here is that the three answers stay three: "not enough to say" must never
 * render as "unchanged", because a photographer who has not been out since has
 * not had advice fail on them.
 */
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import ExperimentRecord from './ExperimentRecord.vue'

const stubs = { RouterLink: { template: '<a><slot /></a>' } }

function experiment(extra = {}) {
  return {
    id: 'experiment_1',
    type: 'explore',
    technique_id: 'low_angle',
    title: 'Get under it.',
    criteria: { exif: {}, text: ['The camera is below the subject.'] },
    verdicts: [],
    status: 'completed',
    issued_at: '2026-08-20T10:00:00Z',
    baseline: {
      source: 'placement',
      citation: '12 of 18 readable shots: centred',
      at_issue: { centred: 12 },
      calc_version: 'tendency-1',
      provenance: { sample_size: 18, calc_version: 'tendency-1', shot_ids: [], model: '' },
    },
    change: null,
    ...extra,
  }
}

function open(props) {
  const wrapper = mount(ExperimentRecord, { props, global: { stubs } })
  wrapper.find('button').trigger('click')
  return wrapper
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('ExperimentRecord', () => {
  it('shows the measurement it was aimed at, verbatim', async () => {
    const wrapper = open({ experiment: experiment() })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('12 of 18 readable shots: centred')
    expect(wrapper.text()).toContain('Measured before it was set')
  })

  it('names the sample the baseline was computed over', async () => {
    const wrapper = open({ experiment: experiment() })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('18 frames')
    expect(wrapper.text()).toContain('tendency-1')
  })

  it('says nothing about a sample an older baseline never recorded', async () => {
    const stale = experiment({
      baseline: { ...experiment().baseline, provenance: { sample_size: 0, calc_version: '' } },
    })
    const wrapper = open({ experiment: stale })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).not.toContain('Baseline computed from')
  })

  it('keeps "not enough to say" distinct from "unchanged"', async () => {
    const wrapper = open({
      experiment: experiment({
        change: {
          state: 'insufficient evidence',
          comparability: 'too few shots',
          outcome: 'nothing shot since',
          added: 0,
        },
      }),
    })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('not enough to say')
    expect(wrapper.text()).toContain('nothing shot since')
    expect(wrapper.text()).not.toContain('unchanged')
  })

  it('never presents a change as something the experiment caused', async () => {
    const wrapper = open({
      experiment: experiment({
        change: {
          state: 'changed',
          comparability: 'comparable',
          outcome: 'first near the edge in 6 shots since',
          added: 6,
        },
      }),
    })
    await wrapper.vm.$nextTick()
    const text = wrapper.text()
    expect(text).toContain('first near the edge in 6 shots since')
    expect(text).toContain('does not show that the experiment caused this')
    expect(text).not.toMatch(/because|worked|improved/i)
  })

  it('says a record has not been checked rather than implying nothing changed', async () => {
    const wrapper = open({ experiment: experiment() })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Not checked yet')
  })

  it('reports the verdict against criteria, never as a pass for the photographer', async () => {
    const wrapper = open({
      experiment: experiment({
        verdicts: [
          {
            shot_id: 'shot_1',
            criteria_met: true,
            feedback: 'Low and close. Next: get lower still.',
            compared_with: '',
          },
        ],
      }),
    })
    await wrapper.vm.$nextTick()
    const text = wrapper.text()
    expect(text).toContain('criteria met')
    expect(text).not.toContain('Passed')
  })
})
