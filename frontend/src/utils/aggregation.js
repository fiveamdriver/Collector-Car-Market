const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function monthKey(monthStr) {
  const [mon, year] = monthStr.split(' ')
  return parseInt(year) * 12 + MONTHS.indexOf(mon)
}

function formatMonth(dateStr) {
  // dateStr is "YYYY-MM-DD"
  const [year, month] = dateStr.split('-')
  return `${MONTHS[parseInt(month) - 1]} ${year}`
}

// Epoch ms for a "Mon YYYY" label. The price chart plots against a real time
// scale, so a year with no sales occupies a year of width instead of collapsing
// to nothing — sales are sparse and irregular, and an evenly-spaced axis makes a
// two-year gap look like a one-month step.
function monthTimestamp(monthStr) {
  const [mon, year] = monthStr.split(' ')
  return Date.UTC(parseInt(year), MONTHS.indexOf(mon), 1)
}

export function groupByMonth(results) {
  const map = Object.create(null) // no prototype — field values can't collide with Object.prototype keys
  for (const r of results) {
    if (!r.sold_date || r.sold_price == null) continue
    const month = formatMonth(r.sold_date)
    if (!map[month]) map[month] = { total: 0, count: 0 }
    map[month].total += r.sold_price
    map[month].count += 1
  }
  return Object.entries(map)
    .map(([month, { total, count }]) => ({
      month,
      t: monthTimestamp(month),
      avgPrice: Math.round(total / count),
      count,
    }))
    .sort((a, b) => a.t - b.t)
}

export function filterByTimeRange(monthlyData, range) {
  if (range === 'All' || !monthlyData.length) return monthlyData
  const cutoffMonths = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12 }[range]
  const now = new Date()
  const cutoffKey = (now.getFullYear()) * 12 + now.getMonth() - cutoffMonths
  return monthlyData.filter(d => monthKey(d.month) >= cutoffKey)
}

export function calcStats(results) {
  if (!results.length) return { avg: 0, high: 0, low: 0, count: 0 }
  // Single pass, no spread: Math.max(...prices) blows the argument-count
  // limit once a result set gets large enough.
  let sum = 0, n = 0, high = 0, low = Infinity
  for (const r of results) {
    const p = r.sold_price
    if (p == null) continue
    sum += p
    n += 1
    if (p > high) high = p
    if (p < low)  low = p
  }
  return {
    avg:   n ? Math.round(sum / n) : 0,
    high:  n ? high : 0,
    low:   n ? low : 0,
    count: results.length,
  }
}

export function groupByField(results, field) {
  const map = Object.create(null) // no prototype — field values can't collide with Object.prototype keys
  for (const r of results) {
    const key = r[field]
    if (!map[key]) map[key] = []
    map[key].push(r)
  }
  return map
}

// --- Server-side aggregate adapters ---
//
// /stats/aggregate returns per-group totals instead of rows. These translate
// that payload into the shapes the existing components already consume, so
// Sparkline, PriceHistoryChart, and the cards stay untouched.

export const EMPTY_STATS = { avg: 0, high: 0, low: 0, count: 0 }

// One API group -> the same shape calcStats produces.
export function statsFromGroup(group) {
  if (!group || !group.count) return EMPTY_STATS
  return {
    avg:   group.avg_sold_price ?? 0,
    high:  group.max_sold_price ?? 0,
    low:   group.min_sold_price ?? 0,
    count: group.count,
  }
}

// Several groups rolled into one card (e.g. 997.1 + 997.2 shown as "997").
// Averages are rebuilt from exact sums so they don't drift the way re-averaging
// rounded per-group averages would.
export function combineStats(groups) {
  const present = groups.filter(g => g && g.count)
  if (!present.length) return EMPTY_STATS
  let sum = 0, priced = 0, count = 0, high = 0, low = Infinity
  for (const g of present) {
    sum    += g.sum_sold_price ?? 0
    priced += g.priced_count ?? 0
    count  += g.count
    if (g.max_sold_price != null && g.max_sold_price > high) high = g.max_sold_price
    if (g.min_sold_price != null && g.min_sold_price < low)  low  = g.min_sold_price
  }
  return {
    avg:   priced ? Math.round(sum / priced) : 0,
    high:  priced ? high : 0,
    low:   priced ? low : 0,
    count,
  }
}

// API monthly points ("YYYY-MM") -> the {month: "Jan 2024", avgPrice, count}
// shape Sparkline, PriceHistoryChart, and filterByTimeRange expect.
export function toMonthlySeries(monthly) {
  if (!monthly?.length) return []
  return monthly.map(({ month, avg_price, count }) => {
    const [year, mon] = month.split('-')
    const label = `${MONTHS[parseInt(mon) - 1]} ${year}`
    return {
      month: label,
      t: monthTimestamp(label),
      avgPrice: avg_price,
      count,
    }
  })
}

// Merge several groups' monthly points, still in API shape ("YYYY-MM"),
// re-averaging by exact totals rather than averaging the averages.
function mergeMonthly(groups) {
  const map = Object.create(null)
  for (const g of groups) {
    for (const p of g?.monthly ?? []) {
      if (!map[p.month]) map[p.month] = { sum_price: 0, count: 0 }
      map[p.month].sum_price += p.sum_price
      map[p.month].count     += p.count
    }
  }
  return Object.entries(map)
    .map(([month, { sum_price, count }]) => ({
      month,
      avg_price: Math.round(sum_price / count),
      count,
      sum_price,
    }))
    .sort((a, b) => a.month.localeCompare(b.month)) // "YYYY-MM" sorts lexically
}

// Merge the monthly series of several groups into one display-ready line.
export function combineMonthly(groups) {
  return toMonthlySeries(mergeMonthly(groups))
}

// Build an API-shaped group from raw auction rows. Needed where rows can't be
// aggregated server-side — cross-listed lots are picked out by id or title
// pattern, which the database grouping has no way to express.
export function groupStatsFromRows(key, rows) {
  let sum = 0, priced = 0, high = 0, low = Infinity
  const months = Object.create(null)
  for (const r of rows) {
    const p = r.sold_price
    if (p == null) continue
    sum += p
    priced += 1
    if (p > high) high = p
    if (p < low)  low  = p
    if (!r.sold_date) continue
    const m = r.sold_date.slice(0, 7) // "YYYY-MM-DD" -> "YYYY-MM"
    if (!months[m]) months[m] = { sum_price: 0, count: 0 }
    months[m].sum_price += p
    months[m].count     += 1
  }
  return {
    key,
    count: rows.length,
    priced_count: priced,
    avg_sold_price: priced ? Math.round(sum / priced) : null,
    min_sold_price: priced ? low : null,
    max_sold_price: priced ? high : null,
    sum_sold_price: sum,
    monthly: Object.entries(months)
      .map(([month, { sum_price, count }]) => ({
        month,
        avg_price: Math.round(sum_price / count),
        count,
        sum_price,
      }))
      .sort((a, b) => a.month.localeCompare(b.month)),
  }
}

// Fold groups into a single API-shaped group, so the result can still feed
// statsFromGroup / toMonthlySeries downstream.
export function mergeGroups(...groups) {
  const present = groups.filter(g => g && g.count)
  if (!present.length) return null
  const totals = combineStats(present)
  return {
    key: present[0].key,
    count: totals.count,
    priced_count: present.reduce((n, g) => n + (g.priced_count ?? 0), 0),
    avg_sold_price: totals.avg || null,
    min_sold_price: totals.low || null,
    max_sold_price: totals.high || null,
    sum_sold_price: present.reduce((n, g) => n + (g.sum_sold_price ?? 0), 0),
    monthly: mergeMonthly(present),
  }
}

// Index an /stats/aggregate response by group key.
export function indexByKey(groups) {
  const map = Object.create(null)
  for (const g of groups) map[g.key] = g
  return map
}
