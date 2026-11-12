// Filtering for a market page's sold results. The results table, the stats
// bar and the price chart all read the same filtered rows, so a PTS-only
// table never sits under all-car averages.

// options / provenance are stored as comma-separated labels.
export function listOf(csv) {
  return csv ? csv.split(',').filter(Boolean) : []
}

// "Club Sport" and "Clubsport" are the same word to a reader.
export const squash = s => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '')

// Filter chips: every tag a car can carry, in the order collectors rank them.
export const FILTER_TAGS = ['PTS', 'Canepa', 'Sonderwunsch', 'Lightweight', 'N/GT', 'Weissach', 'M491', 'Clubsport',
                            'Touring Package', 'X50/X51']

export function hasTag(r, t) {
  if (t === 'PTS') return !!r.paint_to_sample
  return listOf(r.options).includes(t) || listOf(r.provenance).includes(t)
}

// Chips for this page: tags some cars have, minus ones every car has or that
// only repeat the variant's own name (Clubsport on the Club Sport card).
export function pageTagsFor(results) {
  const variant = squash(results[0]?.variant)
  return FILTER_TAGS.filter(t => {
    const n = results.filter(r => hasTag(r, t)).length
    return n > 0 && n < results.length && !(variant && variant.includes(squash(t)))
  })
}

export const NO_FILTERS = Object.freeze({ year: null, tags: [] })

// Selected tags that exist on this page. A tag carried over from another page
// must not filter everything out.
export function activeTagsFor(filters, pageTags) {
  return (filters.tags ?? []).filter(t => pageTags.includes(t))
}

export function isFiltered(filters, pageTags) {
  return filters.year != null || activeTagsFor(filters, pageTags).length > 0
}

export function filterByYear(results, year) {
  return year != null ? results.filter(r => r.year === year) : results
}

// Year, then every selected tag (PTS + Leichtbau = lightweight PTS cars).
export function applyFilters(results, filters, pageTags = pageTagsFor(results)) {
  const tags = activeTagsFor(filters, pageTags)
  return filterByYear(results, filters.year).filter(r => tags.every(t => hasTag(r, t)))
}
