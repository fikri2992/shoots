/**
 * The photographer's guide, in frame units (0-1), independent of the cell grid.
 *
 * The cell mesh (A1..G9) is how the model points at things. A guide is how a
 * photographer reads a frame — thirds, the phi grid, the diagonal method, a
 * centre axis — and what they want to know is whether the frame is sitting on
 * it. So these return lines and landing points, and `offset` says how far the
 * subject is from the nearest one.
 *
 * Which guide is chosen lives in the backend (`domain/guides.py`) and arrives
 * on `analysis.composition.guide`; this file only knows how to draw them.
 */

const PHI = 0.382 // 1 : 0.618 : 1

export const GUIDES = ['thirds', 'phi', 'diagonals', 'centre', 'fill', 'none']

export const GUIDE_LABELS = {
  thirds: 'thirds',
  phi: 'phi',
  diagonals: 'diagonals',
  centre: 'centre',
  fill: 'frame',
  none: 'off',
}

/**
 * Lines and power points for a guide, in frame units. `aspect` is width/height
 * in pixels: the diagonal method's corner bisectors are 45° on the print, not
 * 45° in normalised space, so they need it.
 */
export function geometry(guide, aspect = 1) {
  if (guide === 'centre') {
    return {
      lines: [
        { x1: 0.5, y1: 0, x2: 0.5, y2: 1 },
        { x1: 0, y1: 0.5, x2: 1, y2: 0.5 },
      ],
      points: [{ x: 0.5, y: 0.5 }],
    }
  }

  if (guide === 'diagonals') {
    // The diagonal method: the two diagonals, plus a 45° bisector from each
    // corner, which is where a subject placed on a diagonal wants to sit.
    const dx = Math.min(1, 1 / aspect)
    const dy = Math.min(1, aspect)
    return {
      lines: [
        { x1: 0, y1: 0, x2: 1, y2: 1 },
        { x1: 1, y1: 0, x2: 0, y2: 1 },
        { x1: 0, y1: 0, x2: dx, y2: dy },
        { x1: 1, y1: 0, x2: 1 - dx, y2: dy },
        { x1: 0, y1: 1, x2: dx, y2: 1 - dy },
        { x1: 1, y1: 1, x2: 1 - dx, y2: 1 - dy },
      ],
      points: [],
    }
  }

  if (guide === 'thirds' || guide === 'phi') {
    const at = guide === 'phi' ? [PHI, 1 - PHI] : [1 / 3, 2 / 3]
    const lines = []
    const points = []
    for (const f of at) {
      lines.push({ x1: f, y1: 0, x2: f, y2: 1 })
      lines.push({ x1: 0, y1: f, x2: 1, y2: f })
    }
    for (const x of at) for (const y of at) points.push({ x, y })
    return { lines, points }
  }

  return { lines: [], points: [] }
}

/** Nearest landing point, and how far the subject sits from it. */
export function offset(guide, point) {
  const { points } = geometry(guide)
  if (!point || !points.length) return null
  let best = null
  for (const candidate of points) {
    const distance = Math.hypot(candidate.x - point.x, candidate.y - point.y)
    if (!best || distance < best.distance) best = { point: candidate, distance }
  }
  return best
}

/**
 * What to tell the photographer about the fit — but only when the read is
 * precise enough to say it. Cells quantise to a seventh of the width, so
 * without a sub-cell subject point there is no honest number to print.
 */
export function verdict(guide, point, { cellWidth = 1 / 7 } = {}) {
  if (guide === 'none' || !point) return ''
  const near = offset(guide, point)
  if (!near) return ''
  const percent = Math.round(near.distance * 100)
  if (near.distance < cellWidth / 2) return `sitting on the ${label(guide)}`
  return `${percent}% of the frame off the nearest ${label(guide)}`
}

function label(guide) {
  if (guide === 'centre') return 'centre'
  if (guide === 'phi') return 'phi point'
  return 'thirds point'
}
