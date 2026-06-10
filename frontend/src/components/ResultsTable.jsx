function fmtPrice(n) {
  return n != null ? `$${n.toLocaleString()}` : '—'
}
function fmtMileage(n) {
  return n != null ? n.toLocaleString() : '—'
}
function truncate(s, n) {
  return s && s.length > n ? s.slice(0, n) + '…' : (s ?? '—')
}
function stripYear(s, stripMileage) {
  if (!s) return s
  let out = s.replace(/\b(?:19|20)\d{2}\b\s*/, '').trim()
  if (stripMileage)
    out = out.replace(/(?:No Reserve:\s+)?[\d,k]+-(?:Mile|Kilometer)\s*/i, '').trim()
  return out
}

export default function ResultsTable({ results }) {
  const sorted = [...results].sort(
    (a, b) => new Date(b.sold_date) - new Date(a.sold_date)
  )

  const showTrans = !results.every(r => r.transmission === results[0]?.transmission)

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Year</th>
            <th>Listing</th>
            {showTrans && <th>Trans</th>}
            <th>Photo</th>
            <th>Mileage</th>
            <th>Sold Price</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={r.id} className={i % 2 === 1 ? 'row-alt' : ''}>
              <td>{r.sold_date}</td>
              <td>{r.year}</td>
              <td className="td-listing">{truncate(stripYear(r.lot_title, r.mileage != null), 40)}</td>
              {showTrans && <td className="td-trans">{r.transmission}</td>}
              <td className="td-photo">
                {r.thumbnail_url
                  ? <img src={r.thumbnail_url} alt="" className="result-thumb" />
                  : '—'}
              </td>
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
  )
}
