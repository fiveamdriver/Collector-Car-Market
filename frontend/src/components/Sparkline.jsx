import { LineChart, Line, ResponsiveContainer } from 'recharts'

const C_LINE = '#5a9e6f'  // sparkline green — used only for variant index cards

export default function Sparkline({ data }) {
  if (!data || data.length < 2) return <div className="sparkline-empty" />
  return (
    <div className="sparkline">
      <ResponsiveContainer width="100%" height={36}>
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="avgPrice"
            stroke={C_LINE}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
