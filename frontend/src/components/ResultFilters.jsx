import { GEARBOXES, EMPTY_FILTERS, isFiltered } from '../utils/resultFilters'

// Chips only appear when they would match something on this page: no Weissach
// chip on a 356, no PDK chip on a 993.
export default function ResultFilters({ counts, filters, onChange, shown, total }) {
  const gearboxes = GEARBOXES.filter(g => counts.gearbox[g] > 0)
  const showGearbox = gearboxes.length > 0
  if (!showGearbox && !counts.pts && !counts.weissach) return null

  const set = patch => onChange({ ...filters, ...patch })
  const chip = (label, count, on, onClick) => (
    <button
      key={label}
      className={`filter-chip${on ? ' filter-chip--on' : ''}`}
      aria-pressed={on}
      onClick={onClick}
    >
      {label}<span className="filter-chip-count">{count}</span>
    </button>
  )

  return (
    <div className="result-filters" role="group" aria-label="Filter results">
      {showGearbox && (
        <div className="filter-group">
          {gearboxes.map(g => chip(g, counts.gearbox[g], filters.gearbox === g,
            () => set({ gearbox: filters.gearbox === g ? null : g })))}
        </div>
      )}
      {(counts.pts > 0 || counts.weissach > 0) && (
        <div className="filter-group">
          {counts.pts > 0 && chip('Paint to Sample', counts.pts, filters.pts,
            () => set({ pts: !filters.pts }))}
          {counts.weissach > 0 && chip('Weissach', counts.weissach, filters.weissach,
            () => set({ weissach: !filters.weissach }))}
        </div>
      )}
      {isFiltered(filters) && (
        <span className="filter-summary">
          {shown} of {total}
          <button className="filter-clear" onClick={() => onChange(EMPTY_FILTERS)}>Clear</button>
        </span>
      )}
      {showGearbox && filters.gearbox && counts.unknownGearbox > 0 && (
        <span className="filter-note">
          {counts.unknownGearbox} with an unlisted gearbox are left out
        </span>
      )}
    </div>
  )
}
