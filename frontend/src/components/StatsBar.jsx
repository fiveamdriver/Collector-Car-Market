function fmt(n) {
  return n ? `$${n.toLocaleString()}` : '—'
}

export default function StatsBar({ avg, high, low, count }) {
  return (
    <div className="stats-bar">
      <div className="stat">
        <span className="stat-label">Avg Sale</span>
        <span className="stat-value">{fmt(avg)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">High</span>
        <span className="stat-value">{fmt(high)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Low</span>
        <span className="stat-value">{fmt(low)}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Sales</span>
        <span className="stat-value">{count}</span>
      </div>
    </div>
  )
}
