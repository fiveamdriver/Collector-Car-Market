// Filters over a market page's auction results. They narrow everything on the
// page (stats, price chart, results), so "Manual" answers "what do manual cars
// sell for", not just "show me the manual ones".
//
// A result with an unknown value is excluded from every option of that filter:
// transmission is NULL when the listing didn't say, and those cars must not be
// counted as manuals. (Until 2026-11 every ingest defaulted to "Manual".)

export const GEARBOXES = ['Manual', 'PDK', 'Automatic']

export const EMPTY_FILTERS = { gearbox: null, pts: false, weissach: false }

export function listOf(csv) {
  return csv ? csv.split(',').filter(Boolean) : []
}

const isPts      = r => r.paint_to_sample === true
const isWeissach = r => listOf(r.options).includes('Weissach')

export function applyFilters(results, f) {
  return results.filter(r =>
    (!f.gearbox  || r.transmission === f.gearbox) &&
    (!f.pts      || isPts(r)) &&
    (!f.weissach || isWeissach(r)))
}

export function filterCounts(results) {
  const gearbox = Object.fromEntries(GEARBOXES.map(g => [g, 0]))
  let pts = 0, weissach = 0, unknownGearbox = 0
  for (const r of results) {
    if (r.transmission in gearbox) gearbox[r.transmission] += 1
    else unknownGearbox += 1
    if (isPts(r)) pts += 1
    if (isWeissach(r)) weissach += 1
  }
  return { gearbox, unknownGearbox, pts, weissach }
}

export function isFiltered(f) {
  return !!(f.gearbox || f.pts || f.weissach)
}
