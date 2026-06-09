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

export default function PriceHistoryChart({ monthlyData }) {
  const [range, setRange] = useState('All')
  const visible = filterByTimeRange(monthlyData, range)

  return (
    <div className="price-chart">
      <div className="chart-header">
        <span className="chart-label">Price History</span>
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
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={visible} margin={{ top: 8, right: 24, bottom: 0, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fill: '#555', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#252525' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={fmtAxis}
            tick={{ fill: '#555', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={56}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2a2a' }} />
          <Line
            type="monotone"
            dataKey="avgPrice"
            stroke="#e8e8e8"
            strokeWidth={2}
            dot={{ r: 3, fill: '#e8e8e8', strokeWidth: 0 }}
            activeDot={{ r: 5, fill: '#ffffff' }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
