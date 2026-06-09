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

      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={visible} margin={{ top: 8, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#191919" vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fill: '#4a4a4a', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#222' }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={fmtAxis}
            tick={{ fill: '#4a4a4a', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={62}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#252525', strokeWidth: 1 }} />
          <Line
            type="monotone"
            dataKey="avgPrice"
            stroke="#c4a35a"
            strokeWidth={2}
            dot={{ r: 3, fill: '#c4a35a', strokeWidth: 0 }}
            activeDot={{ r: 5, fill: '#d4b36a', strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
