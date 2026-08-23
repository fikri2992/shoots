import { describe, expect, it } from 'vitest'

import { geometry, offset, verdict } from './guides'

describe('guides', () => {
  it('puts the thirds lines and power points where a photographer expects them', () => {
    const { lines, points } = geometry('thirds')
    expect(lines).toHaveLength(4)
    expect(points).toHaveLength(4)
    expect(points[0]).toEqual({ x: 1 / 3, y: 1 / 3 })
    expect(lines[0]).toEqual({ x1: 1 / 3, y1: 0, x2: 1 / 3, y2: 1 })
  })

  it('uses 1:0.618:1 for the phi grid, which is not the same as thirds', () => {
    const phi = geometry('phi').points.map((p) => p.x)
    expect(phi[0]).toBeCloseTo(0.382, 3)
    expect(phi[0]).not.toBeCloseTo(1 / 3, 3)
  })

  it('keeps the corner bisectors at 45 degrees on the print, not in the maths', () => {
    // Landscape 2:1 — a 45° line reaches half the width by the time it reaches
    // the bottom, so its endpoint is (0.5, 1) in frame units.
    const bisector = (aspect) =>
      geometry('diagonals', aspect)
        .lines.filter((l) => l.x1 === 0 && l.y1 === 0)
        .find((l) => !(l.x2 === 1 && l.y2 === 1))
    expect(bisector(2)).toEqual({ x1: 0, y1: 0, x2: 0.5, y2: 1 })
    expect(bisector(0.5)).toEqual({ x1: 0, y1: 0, x2: 1, y2: 0.5 })
  })

  it('finds the nearest landing point', () => {
    const near = offset('thirds', { x: 0.36, y: 0.3 })
    expect(near.point).toEqual({ x: 1 / 3, y: 1 / 3 })
    expect(near.distance).toBeLessThan(0.05)
  })

  it('only claims a fit when the read is finer than the cell grid', () => {
    expect(verdict('thirds', { x: 1 / 3, y: 1 / 3 })).toBe('sitting on the thirds point')
    expect(verdict('thirds', { x: 0.5, y: 0.5 })).toMatch(/% of the frame off/)
    expect(verdict('none', { x: 0.5, y: 0.5 })).toBe('')
    expect(verdict('thirds', null)).toBe('')
  })
})
