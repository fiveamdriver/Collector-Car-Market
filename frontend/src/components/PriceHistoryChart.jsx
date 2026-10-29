import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { filterByTimeRange } from '../utils/aggregation'

const RANGES = ['1M', '3M', '6M', '1Y', 'All']

const C_GRID   = '#D5D2CC'  // --border
const C_TEXT   = '#555555'  // --text-secondary
const C_CURSOR = '#C8C5BF'  // --border-light
const C_LINE   = '#6B6B6B'  // darker than the old #888 — 2px of it sat too close to the surface
const C_DOT    = '#4A4A4A'

function fmtAxis(n) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}k`
  return `$${n}`
}

const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

// Ticks on real calendar boundaries, thinned so labels never collide. Anchoring
// to the calendar — rather than to whichever months happen to hold a sale — is
// what makes the spacing readable as time. Short ranges get months, because a
// single "2026" tick tells the reader nothing.
function axisTime(data) {
  const yearOnly = t => String(new Date(t).getUTCFullYear())
  if (data.length < 2) return { ticks: undefined, format: yearOnly }

  const a = new Date(data[0].t)
  const b = new Date(data[data.length - 1].t)
  const months = (b.getUTCFullYear() - a.getUTCFullYear()) * 12
              + (b.getUTCMonth() - a.getUTCMonth())

  if (months <= 30) {
    const step = months <= 8 ? 1 : months <= 16 ? 2 : 3
    const ticks = []
    let y = a.getUTCFullYear(), m = a.getUTCMonth()
    while (Date.UTC(y, m, 1) <= b.getTime()) {
      ticks.push(Date.UTC(y, m, 1))
      m += step
      while (m > 11) { m -= 12; y += 1 }
    }
    return {
      ticks,
      // Year on the first tick and each January only — enough to place the range
      // without repeating itself across every label.
      format: t => {
        const d = new Date(t)
        return (t === ticks[0] || d.getUTCMonth() === 0)
          ? `${MON[d.getUTCMonth()]} ${d.getUTCFullYear()}`
          : MON[d.getUTCMonth()]
      },
    }
  }

  const first = a.getUTCFullYear(), last = b.getUTCFullYear()
  const step  = (last - first) <= 6 ? 1 : (last - first) <= 14 ? 2 : 5
  const ticks = []
  for (let y = Math.ceil(first / step) * step; y <= last; y += step) {
    ticks.push(Date.UTC(y, 0, 1))
  }
  return { ticks: ticks.length >= 2 ? ticks : undefined, format: yearOnly }
}

// A month whose "average" is one sale is far weaker evidence than a month with
// six. Area scales with the sale count so the eye weights them accordingly,
// instead of reading every point as an equally solid price.
function countRadius(count) {
  return Math.min(6, 2.5 + Math.sqrt(Math.max(count, 1) - 1) * 1.1)
}

function PriceDot({ cx, cy, payload }) {
  if (cx == null || cy == null) return null
  return (
    <circle
      cx={cx} cy={cy} r={countRadius(payload.count)}
      fill={C_LINE} stroke="var(--surface, #EAE8E3)" strokeWidth={1.5}
    />
  )
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { avgPrice, count, month } = payload[0].payload
  return (
    <div className="chart-tooltip">
      <div className="tt-month">{month}</div>
      <div className="tt-price">{fmtAxis(avgPrice)}</div>
      <div className="tt-count">
        {count === 1 ? '1 sale' : `${count} sales · avg`}
      </div>
    </div>
  )
}

export default function PriceHistoryChart({ monthlyData, defaultExpanded = true }) {
  const [range, setRange] = useState('All')
  const [expanded, setExpanded] = useState(defaultExpanded)
  const visible = filterByTimeRange(monthlyData, range)
  const axis = axisTime(visible)

  return (
    <div className={`price-chart${expanded ? '' : ' price-chart--collapsed'}`}>
      <div className="chart-header">
        <div className="chart-header-left">
          <span className="chart-label">Price History</span>
          <button
            className="chart-toggle"
            onClick={() => setExpanded(e => !e)}
            aria-label={expanded ? 'Collapse chart' : 'Expand chart'}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              {expanded
                ? <polyline points="2,8 6,4 10,8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                : <polyline points="2,4 6,8 10,4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              }
            </svg>
          </button>
        </div>
        {expanded && (
          <div className="range-toggles">
            {RANGES.map(r => (
              <button
                key={r}
                className={`range-btn${range === r ? ' active' : ''}`}
                onClick={() => setRange(r)}
              >
                {r}
              </button>
            ))}
          </div>
        )}
      </div>

      {expanded && (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={visible} margin={{ top: 10, right: 24, bottom: 4, left: 8 }}>
            {/* Solid hairline: a dashed grid reads as a threshold or projection. */}
            <CartesianGrid stroke={C_GRID} strokeWidth={1} vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              ticks={axis.ticks}
              tickFormatter={axis.format}
              tick={{ fill: C_TEXT, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: C_GRID }}
            />
            <YAxis
              tickFormatter={fmtAxis}
              tick={{ fill: C_TEXT, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={62}
              // Fit the band the prices actually occupy. Anchoring at $0 spent a
              // quarter of the height on empty space and flattened the variation.
              domain={[
                min => Math.max(0, min - (min * 0.12)),
                max => max + (max * 0.08),
              ]}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: C_CURSOR, strokeWidth: 1 }} />
            <Line
              // Linear, not monotone: a smoothed curve invents prices between two
              // sales that may be years apart.
              type="linear"
              dataKey="avgPrice"
              stroke={C_LINE}
              strokeWidth={2}
              dot={<PriceDot />}
              activeDot={{ r: 6, fill: C_DOT, strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
