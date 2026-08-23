/**
 * Cell refs → unit-cell geometry. The backend speaks cells (A1..); the canvas
 * draws an SVG whose viewBox is `0 0 cols rows`, so everything here is in
 * cell units and the browser never touches pixels.
 */

const REF = /^([A-Z])(\d{1,2})$/

export function parseRef(ref) {
  const match = REF.exec(String(ref).trim().toUpperCase())
  if (!match) return null
  const col = match[1].charCodeAt(0) - 65
  const row = Number(match[2]) - 1
  if (row < 0) return null
  return { col, row }
}

/** Smallest box covering every ref, in cell units. Null if none parse. */
export function spanBox(refs) {
  let left = Infinity
  let top = Infinity
  let right = -Infinity
  let bottom = -Infinity
  for (const ref of refs || []) {
    const cell = parseRef(ref)
    if (!cell) continue
    left = Math.min(left, cell.col)
    top = Math.min(top, cell.row)
    right = Math.max(right, cell.col + 1)
    bottom = Math.max(bottom, cell.row + 1)
  }
  if (left === Infinity) return null
  return { x: left, y: top, w: right - left, h: bottom - top }
}

export function center(box) {
  return { x: box.x + box.w / 2, y: box.y + box.h / 2 }
}

/** Arrow geometry from one span to another: line plus a triangular head. */
export function arrow(fromRefs, toRefs, headSize = 0.35) {
  const a = spanBox(fromRefs)
  const b = spanBox(toRefs)
  if (!a || !b) return null
  const start = center(a)
  const end = center(b)
  const angle = Math.atan2(end.y - start.y, end.x - start.x)
  const left = {
    x: end.x - headSize * Math.cos(angle - 0.5),
    y: end.y - headSize * Math.sin(angle - 0.5),
  }
  const right = {
    x: end.x - headSize * Math.cos(angle + 0.5),
    y: end.y - headSize * Math.sin(angle + 0.5),
  }
  return { start, end, head: [end, left, right] }
}

/**
 * Where a span sits, in the words a person would use. The cell grid is how the
 * lenses point at things among themselves; a reader who has never seen that
 * grid — which is all of them — needs "the bottom left", not "C7-E7".
 */
export function place(refs, grid) {
  const box = spanBox(refs)
  if (!box) return ''
  const wide = box.w / grid.cols > 0.6
  const tall = box.h / grid.rows > 0.6
  if (wide && tall) return 'most of the frame'

  const cx = (box.x + box.w / 2) / grid.cols
  const cy = (box.y + box.h / 2) / grid.rows
  const col = cx < 1 / 3 ? 'left' : cx > 2 / 3 ? 'right' : 'centre'
  const row = cy < 1 / 3 ? 'top' : cy > 2 / 3 ? 'bottom' : 'middle'

  if (wide) return row === 'middle' ? 'across the middle' : `across the ${row}`
  if (tall) return col === 'centre' ? 'down the centre' : `down the ${col}`
  if (row === 'middle' && col === 'centre') return 'the centre of the frame'
  // One word on its own ("the bottom") reads like a fragment; two ("the bottom
  // left") does not.
  if (row === 'middle') return `the ${col} of the frame`
  if (col === 'centre') return `the ${row} of the frame`
  return `the ${row} ${col}`
}

/**
 * One cell, or a run of them joined by "to", a dash, a slash or commas —
 * with any preposition that introduces it, since some replacements carry
 * their own ("across the top" must not become "across across the top").
 */
const RUN =
  /(\b(?:across|along|at|in|from|through|between|over|spans|spanning|fills|occupies|covers)\s+)?\b[A-H][1-9]\b(?:\s*(?:[-–—,/]|to|and)\s*\b[A-H][1-9]\b)*/g

/** Words that take a place directly: "spans the top", not "spans across the top". */
const VERBS = /^(spans|spanning|fills|occupies|covers)\s+$/

/**
 * Rewrite cell references in prose as plain positions. The models are told not
 * to write them, but analyses read before that still carry coordinates, and a
 * coordinate the reader cannot see is worse than no locator at all.
 */
export function plain(text, grid) {
  if (!text || !grid) return text || ''
  return text
    .replace(RUN, (run, preposition = '') => {
      const phrase = place(run.match(/[A-H][1-9]/g) || [], grid)
      if (!phrase) return run
      const lead = preposition || ''
      if (!/^(across|down|most) /.test(phrase)) return `${lead}${phrase}`
      // The phrase brings its own preposition: drop the one in the sentence,
      // unless it was a verb, which needs the place without one.
      return VERBS.test(lead) ? `${lead}${phrase.replace(/^(across|down) /, '')}` : phrase
    })
    .replace(/\s{2,}/g, ' ')
    .replace(/\s+([.,])/g, '$1')
}
