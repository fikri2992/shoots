import { describe, expect, it } from 'vitest'

import { arrow, parseRef, spanBox } from './cells'

describe('cells', () => {
  it('parses chess-style refs', () => {
    expect(parseRef('A1')).toEqual({ col: 0, row: 0 })
    expect(parseRef('c4')).toEqual({ col: 2, row: 3 })
    expect(parseRef('Z0')).toBeNull()
    expect(parseRef('nope')).toBeNull()
  })

  it('spans cells into a box in cell units', () => {
    expect(spanBox(['B2'])).toEqual({ x: 1, y: 1, w: 1, h: 1 })
    expect(spanBox(['B2', 'D4', 'bad'])).toEqual({ x: 1, y: 1, w: 3, h: 3 })
    expect(spanBox([])).toBeNull()
  })

  it('builds an arrow between spans', () => {
    const a = arrow(['A1'], ['C1'])
    expect(a.start).toEqual({ x: 0.5, y: 0.5 })
    expect(a.end).toEqual({ x: 2.5, y: 0.5 })
    expect(a.head).toHaveLength(3)
    expect(arrow(['A1'], [])).toBeNull()
  })
})
