import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, MODEL_LINE, VARIANTS } from '../data/taxonomy'
import { fetchAuctionResults } from '../api/client'
import { calcStats, groupByField, groupByMonth } from '../utils/aggregation'
import { toSlug } from '../utils/slugs'
import Breadcrumb from '../components/Breadcrumb'
import Sparkline from '../components/Sparkline'

export default function VariantIndex() {
  const { modelSlug, generation } = useParams()
  const model    = ALL_MODELS.find(m => m.slug === modelSlug)
  const modelLine = MODEL_LINE[modelSlug]
  const variants  = VARIANTS[modelSlug]?.[generation] ?? []

  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchAuctionResults({ model_line: modelLine, generation })
      .then(setResults)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [modelLine, generation])

  const byVariant = useMemo(() => groupByField(results, 'variant'), [results])

  if (!model) return <Navigate to="/" replace />

  return (
    <div className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={[
          { label: 'Markets',   to: '/' },
          { label: model.label, to: `/${modelSlug}` },
          { label: generation },
        ]} />
        <h1 className="page-title">{model.label} {generation}</h1>
      </div>

      {loading && <p className="status">Loading…</p>}
      {error   && <p className="status error">Error: {error}</p>}

      {!loading && !error && (
        <div className="card-grid">
          {variants.map(variant => {
            const varResults = byVariant[variant] ?? []
            const stats   = calcStats(varResults)
            const monthly = groupByMonth(varResults)
            return (
              <Link
                key={variant}
                to={`/${modelSlug}/${generation}/${toSlug(variant)}`}
                className="index-card"
              >
                <div className="index-card-header">
                  <span className="index-card-name">{variant}</span>
                  <span className="index-card-count">{stats.count} sold</span>
                </div>
                {stats.count > 0 && (
                  <div className="index-card-avg">${stats.avg.toLocaleString()} avg</div>
                )}
                <Sparkline data={monthly} />
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
