const C_LINE = '#5a9e6f'  // sparkline green — used only for variant index cards

// Plain SVG instead of recharts: index pages render one sparkline per card,
// and a full LineChart + ResponsiveContainer (ResizeObserver, tooltip layer,
// axis machinery) per 36px trend line is orders of magnitude more work than
// a polyline. viewBox + preserveAspectRatio handles responsiveness for free.
export default function Sparkline({ data }) {
  if (!data || data.length < 2) return <div className="sparkline-empty" />

  const W = 100, H = 36, PAD = 2
  const prices = data.map(d => d.avgPrice)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const span = max - min || 1
  const points = data
    .map((d, i) => {
      const x = PAD + (i / (data.length - 1)) * (W - 2 * PAD)
      const y = PAD + (1 - (d.avgPrice - min) / span) * (H - 2 * PAD)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')

  return (
    <div className="sparkline">
      <svg
        width="100%"
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <polyline
          points={points}
          fill="none"
          stroke={C_LINE}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </div>
  )
}
