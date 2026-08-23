import { describe, expect, it } from 'vitest'

import { arrow, parseRef, place, plain, spanBox } from './cells'

const GRID = { cols: 7, rows: 9 }

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

describe('place', () => {
  it('names a span the way a person would', () => {
    expect(place(['A1'], GRID)).toBe('the top left')
    expect(place(['G9'], GRID)).toBe('the bottom right')
    expect(place(['D5'], GRID)).toBe('the centre of the frame')
    expect(place(['A2', 'G2'], GRID)).toBe('across the top')
    expect(place(['D1', 'D9'], GRID)).toBe('down the centre')
    expect(place(['A1', 'G9'], GRID)).toBe('most of the frame')
    expect(place([], GRID)).toBe('')
  })
})

describe('plain', () => {
  it('rewrites coordinates the reader cannot see', () => {
    expect(plain('The shoes at C7–E7 catch the light.', GRID)).toBe(
      'The shoes at the bottom of the frame catch the light.',
    )
    expect(plain('A cyclist rides away at D1-E2.', GRID)).toBe(
      'A cyclist rides away at the top of the frame.',
    )
  })

  it('does not stack prepositions, and leaves verbs their object', () => {
    expect(plain('The umbrella across B3–F6 dominates.', GRID)).toBe('The umbrella across the middle dominates.')
    expect(plain('The pole spans A2 to G2.', GRID)).toBe('The pole spans the top.')
    expect(plain('The subject fills B4 to E9.', GRID)).toBe('The subject fills the centre.')
  })

  it('leaves prose without coordinates alone', () => {
    const text = 'Bright overcast light, no shadows, a calm frame.'
    expect(plain(text, GRID)).toBe(text)
    expect(plain(text, null)).toBe(text)
  })
})
