import { test } from 'node:test'
import assert from 'node:assert/strict'
import { applyFilters, isFiltered, pageTagsFor, NO_FILTERS } from './resultFilters.js'
import { calcStats } from './aggregation.js'

const cars = [
  { id: 1, year: 1994, variant: 'Speedster', sold_price: 300_000, paint_to_sample: true,  options: 'Lightweight' },
  { id: 2, year: 1994, variant: 'Speedster', sold_price: 150_000, paint_to_sample: false, options: '' },
  { id: 3, year: 1993, variant: 'Speedster', sold_price: 120_000, paint_to_sample: false, options: 'Lightweight' },
  { id: 4, year: 1993, variant: 'Speedster', sold_price: 600_000, paint_to_sample: true,  options: '' },
]

test('no filters keeps every row', () => {
  assert.equal(applyFilters(cars, NO_FILTERS).length, 4)
  assert.equal(isFiltered(NO_FILTERS, pageTagsFor(cars)), false)
})

test('tags are ANDed', () => {
  assert.deepEqual(applyFilters(cars, { year: null, tags: ['PTS'] }).map(r => r.id), [1, 4])
  assert.deepEqual(applyFilters(cars, { year: null, tags: ['PTS', 'Lightweight'] }).map(r => r.id), [1])
})

test('year and tags combine', () => {
  assert.deepEqual(applyFilters(cars, { year: 1993, tags: ['PTS'] }).map(r => r.id), [4])
})

test('a tag that is not on this page is ignored, not an empty result', () => {
  const f = { year: null, tags: ['Weissach'] }
  assert.equal(applyFilters(cars, f).length, 4)
  assert.equal(isFiltered(f, pageTagsFor(cars)), false)
})

test('stats follow the filter (the bug: PTS table under all-car averages)', () => {
  const all = calcStats(cars)
  const pts = calcStats(applyFilters(cars, { year: null, tags: ['PTS'] }))
  assert.equal(pts.count, 2)
  assert.notEqual(pts.avg, all.avg)
  assert.equal(pts.avg, 450_000)
})
