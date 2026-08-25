import { describe, expect, it } from 'vitest'

import { cameraMove, harmony, measured, readout } from './tone'

const tone = (over = {}) => ({
  cct_k: 5594,
  cast: 15,
  saturation: 25,
  saturation_p95: 63,
  accent_share: 9,
  warm_share: 18,
  cool_share: 2,
  luma_mean: 134,
  luma_p5: 32,
  luma_p95: 229,
  clipped_high: 0,
  clipped_low: 0,
  hues: ['teal', 'amber'],
  hue_opposition: 120,
  ...over,
})

const motion = (over = {}) => ({
  frames: 12,
  fps: 4,
  drift_x: 0,
  drift_y: 0,
  step: 0,
  step_max: 0,
  reversals: 0,
  still_share: 0,
  ...over,
})

describe('the measured readout', () => {
  it('names every number it shows', () => {
    for (const row of readout(tone())) {
      expect(row.value).toMatch(/\d/)
      expect(row.label).toBeTruthy()
    }
  })

  it('reads open shade as open shade and tungsten as tungsten', () => {
    const at = (k) => readout(tone({ cct_k: k })).find((r) => r.key === 'temperature').label
    expect(at(8639)).toBe('open shade')
    expect(at(3300)).toBe('tungsten')
    expect(at(5594)).toBe('early or late sun')
    // Below the tungsten floor is candlelight, matching domain/tone.py exactly.
    expect(at(3100)).toBe('candlelight')
  })

  it('omits the temperature when the backend withheld it', () => {
    // A frame too far off the Planckian locus has no colour temperature; the
    // readout must go quiet rather than print "null K".
    const rows = readout(tone({ cct_k: null }))
    expect(rows.find((r) => r.key === 'temperature')).toBeUndefined()
    expect(rows.length).toBeGreaterThan(0)
  })

  it('mentions clipping only at the end that actually ran out', () => {
    expect(readout(tone()).find((r) => r.key === 'clipped')).toBeUndefined()
    expect(readout(tone({ clipped_high: 8.3 })).find((r) => r.key === 'clipped').value).toBe('8.3')
    // Crushed blacks must not be reported as "0.0% blown white".
    const shadows = readout(tone({ clipped_low: 4.1 }))
    expect(shadows.find((r) => r.key === 'clipped')).toBeUndefined()
    expect(shadows.find((r) => r.key === 'crushed').label).toBe('crushed black')
  })

  it('says nothing at all about an unmeasured shot', () => {
    expect(measured(null)).toBe(false)
    expect(readout(null)).toEqual([])
    expect(readout({ cct_k: null, luma_mean: 0 })).toEqual([])
  })

  it('calls two opposed hues opposed and two neighbours neighbouring', () => {
    expect(harmony(tone({ hue_opposition: 180 }))).toBe('teal and amber, opposed')
    expect(harmony(tone({ hue_opposition: 30 }))).toBe('teal and amber, neighbouring')
  })

  it('claims no hue relationship for a frame with almost no colour', () => {
    expect(harmony(tone({ saturation: 9 }))).toBe('')
  })
})

describe('the camera move', () => {
  it('reports a locked frame as locked', () => {
    expect(cameraMove(motion({ still_share: 0.92, drift_x: -0.03 }))).toMatch(/locked off/)
  })

  it('reports a pan with its direction and distance', () => {
    const text = cameraMove(motion({ drift_x: 0.58, step_max: 0.06, still_share: 0.53 }))
    expect(text).toMatch(/pans right/)
    expect(text).toMatch(/0\.6 frame widths/)
  })

  it('separates a whip from a fast pan', () => {
    expect(cameraMove(motion({ drift_x: 2.42, step_max: 0.63 }))).toMatch(/whips right/)
    expect(cameraMove(motion({ drift_x: 2.42, step_max: 0.06 }))).toMatch(/pans right/)
  })

  it('reports a leftward pan as leftward', () => {
    expect(cameraMove(motion({ drift_x: -0.9, step_max: 0.06 }))).toMatch(/pans left/)
  })

  it('says nothing about a photo', () => {
    expect(cameraMove(null)).toBe('')
    expect(cameraMove(motion({ frames: 0 }))).toBe('')
  })
})
