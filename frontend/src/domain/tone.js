/**
 * The measured frame, in the words that go beside the numbers.
 *
 * `Shot.tone` and `Shot.motion` arrive as raw measurements — kelvin, percent,
 * frame widths — because that is what the backend stores and what the lenses
 * reason with. A readout of bare numbers teaches nothing, so the band tables
 * here name them, mirroring `app/domain/tone.py` and `app/domain/motion.py`
 * the way `guides.js` mirrors `guides.py`.
 *
 * The numbers are the point. A photographer can check 8639 K against their own
 * white balance and 1.1% clipped against their own histogram; "cool" and
 * "bright" are the adjectives this whole pass exists to replace.
 */

export const DAYLIGHT_K = 5500

const TEMPERATURE = [
  [7500, 'open shade'],
  [6500, 'overcast'],
  [5800, 'midday sun'],
  [5000, 'early or late sun'],
  [4200, 'warm interior'],
  [3200, 'tungsten'],
  [0, 'candlelight'],
]

const KEY = [
  [170, 'high key'],
  [85, 'mid key'],
  [0, 'low key'],
]

const RANGE = [
  [180, 'full range'],
  [120, 'ordinary range'],
  [0, 'flat'],
]

const PALETTE = [
  [45, 'vivid'],
  [30, 'saturated'],
  [15, 'restrained'],
  [0, 'near-neutral'],
]

function band(value, table) {
  for (const [floor, label] of table) if (value >= floor) return label
  return table[table.length - 1][1]
}

/** Nothing was measured — an old analysis, or a file Pillow could not open. */
export function measured(tone) {
  return Boolean(tone) && (tone.cct_k !== null || tone.luma_mean > 0)
}

/**
 * The readout under the frame: value, unit and the word for it. Temperature is
 * omitted rather than guessed when the frame sits too far off the Planckian
 * locus for a colour temperature to mean anything (a frame of pure red is a red
 * object, not 2655 K light), which is why `cct_k` can be null on a real shot.
 */
export function readout(tone) {
  if (!measured(tone)) return []
  const range = Math.round(tone.luma_p95 - tone.luma_p5)
  const rows = []
  if (tone.cct_k) {
    rows.push({ key: 'temperature', value: `${tone.cct_k}`, unit: 'K', label: band(tone.cct_k, TEMPERATURE) })
  }
  rows.push({ key: 'palette', value: `${Math.round(tone.saturation)}`, unit: '%', label: band(tone.saturation, PALETTE) })
  rows.push({ key: 'range', value: `${range}`, unit: '', label: band(range, RANGE) })
  rows.push({ key: 'key', value: `${Math.round(tone.luma_mean)}`, unit: '', label: band(tone.luma_mean, KEY) })
  // Only the end that actually ran out, and only when it did: a readout saying
  // "0.0% clipped white" is noise dressed as a measurement.
  if (tone.clipped_high >= 0.05) {
    rows.push({ key: 'clipped', value: tone.clipped_high.toFixed(1), unit: '%', label: 'blown white' })
  }
  if (tone.clipped_low >= 0.05) {
    rows.push({ key: 'crushed', value: tone.clipped_low.toFixed(1), unit: '%', label: 'crushed black' })
  }
  return rows
}

/** The two dominant hues and what they are doing, when there is enough colour. */
export function harmony(tone) {
  if (!measured(tone) || !tone.hues?.length || tone.saturation < 15) return ''
  const hues = tone.hues.slice(0, 2).join(' and ')
  if (tone.hue_opposition === null || tone.hue_opposition === undefined) return hues
  if (tone.hue_opposition >= 120) return `${hues}, opposed`
  if (tone.hue_opposition <= 60) return `${hues}, neighbouring`
  return hues
}

/**
 * How the camera travelled, in a phrase. Mirrors `domain/motion.py`, including
 * its silences: translation cannot see rotation, scale or focus, so a push-in
 * or an orbit reads here as "barely moves" and is left to the panel.
 */
export function cameraMove(motion) {
  if (!motion || motion.frames < 2) return ''
  const travel = Math.max(Math.abs(motion.drift_x), Math.abs(motion.drift_y))
  const seconds = motion.fps ? Math.round(motion.frames / motion.fps) : 0
  if (motion.still_share >= 0.75 && travel < 0.25) {
    return `locked off — no movement in ${Math.round(motion.still_share * 100)}% of ${seconds} s`
  }
  if (travel < 0.25) return `barely moves — ${travel.toFixed(2)} frame widths in ${seconds} s`
  const where = Math.abs(motion.drift_x) * 2 > Math.abs(motion.drift_y)
    ? motion.drift_x > 0 ? 'right' : 'left'
    : motion.drift_y > 0 ? 'down' : 'up'
  if (motion.step_max >= 0.25) {
    return `whips ${where} — ${motion.step_max.toFixed(2)} of the frame in one step, ${travel.toFixed(1)} widths in ${seconds} s`
  }
  const shape = Math.abs(motion.drift_x) > Math.abs(motion.drift_y) * 2 ? 'pans' : 'tilts'
  return `${shape} ${where} — ${travel.toFixed(1)} frame widths in ${seconds} s`
}
