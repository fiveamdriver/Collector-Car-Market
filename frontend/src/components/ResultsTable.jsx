import { useEffect, useMemo, useState } from 'react'

function fmtPrice(n) {
  return n != null ? `$${n.toLocaleString()}` : '—'
}
function fmtMileage(n) {
  return n != null ? n.toLocaleString() : '—'
}
function fmtDate(s) {
  if (!s) return '—'
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
function truncate(s, n) {
  return s && s.length > n ? s.slice(0, n) + '…' : (s ?? '—')
}
function stripYear(s, hasMileage) {
  if (!s) return s
  let out = s.replace(/\b(?:19|20)\d{2}\b\s*/, '').trim()
  if (hasMileage)
    out = out.replace(/(?:No Reserve:\s+)?[\d,k]+-(?:Mile|Kilometer)\s*/i, '').trim()
  return out
}
function stripColor(s, color) {
  if (!s || !color) return s
  return s.replace(new RegExp('^' + color.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*', 'i'), '').trim()
}

export default function ResultsTable({ results }) {
  const [lightbox, setLightbox] = useState(null)
  const [openCol, setOpenCol] = useState(null)
  const [dropPos, setDropPos] = useState({ top: 0, left: 0 })
  const [sortBy, setSortBy] = useState('date-desc')
  const [filterYear, setFilterYear] = useState(null)

  useEffect(() => {
    if (!openCol) return
    const close = () => setOpenCol(null)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [openCol])

  const uniqueYears = useMemo(
    () => [...new Set(results.map(r => r.year).filter(Boolean))].sort((a, b) => b - a),
    [results]
  )

  const visible = useMemo(() => {
    let rows = filterYear ? results.filter(r => r.year === filterYear) : [...results]
    // ISO date strings compare correctly as strings; '' sorts null dates last
    // in desc and first in asc instead of NaN-ordering them arbitrarily.
    switch (sortBy) {
      case 'date-desc':  rows.sort((a, b) => (b.sold_date ?? '').localeCompare(a.sold_date ?? '')); break
      case 'date-asc':   rows.sort((a, b) => (a.sold_date ?? '').localeCompare(b.sold_date ?? '')); break
      case 'price-desc': rows.sort((a, b) => (b.sold_price ?? 0) - (a.sold_price ?? 0)); break
      case 'price-asc':  rows.sort((a, b) => (a.sold_price ?? 0) - (b.sold_price ?? 0)); break
    }
    return rows
  }, [results, sortBy, filterYear])

  const openDropdown = (col, e) => {
    e.stopPropagation()
    if (openCol === col) { setOpenCol(null); return }
    const rect = e.currentTarget.getBoundingClientRect()
    setDropPos({ top: rect.bottom + 1, left: rect.left })
    setOpenCol(col)
  }

  const dateArrow   = sortBy === 'date-desc'  ? '↓' : sortBy === 'date-asc'  ? '↑' : null
  const priceArrow  = sortBy === 'price-desc' ? '↓' : sortBy === 'price-asc' ? '↑' : null
  const sortingByDate  = sortBy === 'date-desc' || sortBy === 'date-asc'
  const sortingByPrice = sortBy === 'price-desc' || sortBy === 'price-asc'

  return (
    <>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th
                className={`th-ctrl${openCol === 'date' ? ' th-ctrl--open' : ''}${sortingByDate ? ' th-ctrl--active' : ''}`}
                onClick={e => openDropdown('date', e)}
              >
                <span className="th-ctrl-inner">
                  Date
                  {dateArrow && <span className="th-sort-arrow">{dateArrow}</span>}
                  <span className="th-chevron">▾</span>
                </span>
              </th>

              <th
                className={`th-ctrl${openCol === 'year' ? ' th-ctrl--open' : ''}${filterYear ? ' th-ctrl--active' : ''}`}
                onClick={e => openDropdown('year', e)}
              >
                <span className="th-ctrl-inner">
                  {filterYear ? <span className="th-filter-tag">{filterYear}</span> : 'Year'}
                  <span className="th-chevron">▾</span>
                </span>
              </th>

              <th>Listing</th>
              <th>Photo</th>
              <th>Color</th>
              <th>Mileage</th>

              <th
                className={`th-ctrl${openCol === 'price' ? ' th-ctrl--open' : ''}${sortingByPrice ? ' th-ctrl--active' : ''}`}
                onClick={e => openDropdown('price', e)}
              >
                <span className="th-ctrl-inner">
                  Sold Price
                  {priceArrow && <span className="th-sort-arrow">{priceArrow}</span>}
                  <span className="th-chevron">▾</span>
                </span>
              </th>

              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => (
              <tr key={r.id} className={i % 2 === 1 ? 'row-alt' : ''}>
                <td>{fmtDate(r.sold_date)}</td>
                <td>{r.year}</td>
                <td className="td-listing">{truncate(stripColor(stripYear(r.lot_title, r.mileage != null), r.exterior_color), 40)}</td>
                <td className="td-photo">
                  {r.thumbnail_url
                    ? <img src={r.thumbnail_url} alt="" loading="lazy" decoding="async" className="result-thumb result-thumb--clickable" onClick={() => setLightbox(r.thumbnail_url)} />
                    : '—'}
                </td>
                <td className="td-color">{r.exterior_color ?? '—'}</td>
                <td>{fmtMileage(r.mileage)}</td>
                <td className="price-cell">{fmtPrice(r.sold_price)}</td>
                <td className="source-cell">
                  {r.auction_url
                    ? <a href={r.auction_url} target="_blank" rel="noopener noreferrer" className="source-link">{r.auction_source}</a>
                    : r.auction_source}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {openCol && (
        <div
          className="th-dropdown"
          style={{ top: dropPos.top, left: dropPos.left }}
          onClick={e => e.stopPropagation()}
        >
          {openCol === 'date' && <>
            <button className={`th-drop-item${sortBy === 'date-desc' ? ' th-drop-item--on' : ''}`}
              onClick={() => { setSortBy('date-desc'); setOpenCol(null) }}>Newest First</button>
            <button className={`th-drop-item${sortBy === 'date-asc' ? ' th-drop-item--on' : ''}`}
              onClick={() => { setSortBy('date-asc'); setOpenCol(null) }}>Oldest First</button>
          </>}

          {openCol === 'price' && <>
            <button className={`th-drop-item${sortBy === 'price-desc' ? ' th-drop-item--on' : ''}`}
              onClick={() => { setSortBy('price-desc'); setOpenCol(null) }}>High to Low</button>
            <button className={`th-drop-item${sortBy === 'price-asc' ? ' th-drop-item--on' : ''}`}
              onClick={() => { setSortBy('price-asc'); setOpenCol(null) }}>Low to High</button>
          </>}

          {openCol === 'year' && <>
            <button className={`th-drop-item${!filterYear ? ' th-drop-item--on' : ''}`}
              onClick={() => { setFilterYear(null); setOpenCol(null) }}>All Years</button>
            {uniqueYears.map(y => (
              <button key={y} className={`th-drop-item${filterYear === y ? ' th-drop-item--on' : ''}`}
                onClick={() => { setFilterYear(y); setOpenCol(null) }}>{y}</button>
            ))}
          </>}
        </div>
      )}

      {lightbox && (
        <div className="lightbox-overlay" onClick={() => setLightbox(null)}>
          <img src={lightbox} alt="" className="lightbox-img" />
        </div>
      )}
    </>
  )
}
