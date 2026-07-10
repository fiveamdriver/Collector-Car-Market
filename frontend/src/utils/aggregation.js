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
      avgPrice: Math.round(total / count),
      count,
    }))
    .sort((a, b) => monthKey(a.month) - monthKey(b.month))
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
