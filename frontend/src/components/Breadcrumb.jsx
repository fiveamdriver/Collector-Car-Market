import { Link } from 'react-router-dom'

// crumbs: Array<{ label: string, to?: string }>
// Last crumb has no `to` — it's the current page.
export default function Breadcrumb({ crumbs }) {
  return (
    <nav className="breadcrumb">
      {crumbs.map((c, i) => (
        <span key={i} className="breadcrumb-item">
          {i > 0 && <span className="breadcrumb-sep">/</span>}
          {c.to
            ? <Link to={c.to} className="breadcrumb-link">{c.label}</Link>
            : <span className="breadcrumb-current">{c.label}</span>
          }
        </span>
      ))}
    </nav>
  )
}
