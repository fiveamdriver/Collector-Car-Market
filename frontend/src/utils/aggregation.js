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
  const map = {}
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
  const prices = results.map(r => r.sold_price).filter(p => p != null)
  return {
    avg:   prices.length ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0,
    high:  prices.length ? Math.max(...prices) : 0,
    low:   prices.length ? Math.min(...prices) : 0,
    count: results.length,
  }
}

export function groupByField(results, field) {
  const map = {}
  for (const r of results) {
    const key = r[field]
    if (!map[key]) map[key] = []
    map[key].push(r)
  }
  return map
}
