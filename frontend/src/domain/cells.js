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
