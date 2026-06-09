function fmtPrice(n) {
  return n != null ? `$${n.toLocaleString()}` : '—'
}
function fmtMileage(n) {
  return n != null ? n.toLocaleString() : '—'
}

export default function ResultsTable({ results }) {
  const sorted = [...results].sort(
    (a, b) => new Date(b.sold_date) - new Date(a.sold_date)
  )

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Year</th>
            <th>Variant</th>
            <th>Trans</th>
            <th>Mileage</th>
            <th>Color</th>
            <th>Sold Price</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <tr key={r.id} className={i % 2 === 1 ? 'row-alt' : ''}>
              <td>{r.sold_date}</td>
              <td>{r.year}</td>
              <td className="td-variant">{r.variant}</td>
              <td className="td-trans">{r.transmission}</td>
              <td>{fmtMileage(r.mileage)}</td>
              <td>{r.color ?? '—'}</td>
              <td className="price-cell">{fmtPrice(r.sold_price)}</td>
              <td className="source-cell">{r.auction_source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
