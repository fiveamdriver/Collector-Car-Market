import { useEffect, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GROUP_CHILDREN, MODEL_LINE, TRANSAXLE_META } from '../data/taxonomy'
import { fetchModelLineStats } from '../api/client'
import Breadcrumb from '../components/Breadcrumb'

// A "group" card (e.g. Transaxle) opens into several models, the way the 911
// opens into generations. Each child links to its own variant-model page.
export default function GroupIndex() {
  const { modelSlug } = useParams()
  const model    = ALL_MODELS.find(m => m.slug === modelSlug)
  const children = GROUP_CHILDREN[modelSlug] ?? []

  const [statsByLine, setStatsByLine] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchModelLineStats()
      .then(rows => setStatsByLine(Object.fromEntries(rows.map(r => [r.model_line, r]))))
      .catch(e => setError(e.message))
  }, [])

  if (!model) return <Navigate to="/" replace />

  return (
    <div className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={[{ label: 'Markets', to: '/' }, { label: model.label }]} />
        <h1 className="page-title">{model.label}</h1>
      </div>

      {error && <p className="status error">Error: {error}</p>}

      <div className="card-grid card-grid--4col">
        {children.map(childSlug => {
          const child = ALL_MODELS.find(m => m.slug === childSlug)
          const meta  = TRANSAXLE_META[childSlug] ?? {}
          const s     = statsByLine[MODEL_LINE[childSlug]]
          const count = s?.count ?? 0
          const avg   = s?.avg_sold_price ?? 0
          return (
            <Link key={childSlug} to={`/${childSlug}`} className="index-card">
              {meta.img && (
                <div className="index-card-img-wrap">
                  <img src={meta.img} alt={child?.label} className="index-card-img" loading="lazy" decoding="async" />
                </div>
              )}
              <div className="index-card-body">
                <span className="index-card-name">{child?.label}</span>
                {meta.years && <span className="index-card-years">{meta.years}</span>}
                {count > 0 && (
                  <>
                    <span className="index-card-price">${avg.toLocaleString()} <span className="index-card-price-label">avg price</span></span>
                    <span className="index-card-count">{count.toLocaleString()} sold</span>
                  </>
                )}
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
