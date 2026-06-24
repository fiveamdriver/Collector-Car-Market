import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { filterByTimeRange } from '../utils/aggregation'

const RANGES = ['1M', '3M', '6M', '1Y', 'All']

function fmtAxis(n) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}k`
  return `$${n}`
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const { avgPrice, count } = payload[0].payload
  return (
    <div className="chart-tooltip">
      <div className="tt-month">{label}</div>
      <div className="tt-price">{fmtAxis(avgPrice)}</div>
      <div className="tt-count">{count} sale{count !== 1 ? 's' : ''}</div>
    </div>
  )
}

export default function PriceHistoryChart({ monthlyData, defaultExpanded = true }) {
  const [range, setRange] = useState('All')
  const [expanded, setExpanded] = useState(defaultExpanded)
  const visible = filterByTimeRange(monthlyData, range)

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
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={visible} margin={{ top: 8, right: 24, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#D5D2CC" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fill: '#555555', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#D5D2CC' }}
              interval="preserveStartEnd"
            />
            <YAxis
              tickFormatter={fmtAxis}
              tick={{ fill: '#555555', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={62}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#C8C5BF', strokeWidth: 1 }} />
            <Line
              type="monotone"
              dataKey="avgPrice"
              stroke="#888888"
              strokeWidth={2}
              dot={{ r: 3, fill: '#888888', strokeWidth: 0 }}
              activeDot={{ r: 5, fill: '#555555', strokeWidth: 0 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
