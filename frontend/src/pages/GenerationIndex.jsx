import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATIONS, MODEL_LINE } from '../data/taxonomy'
import { fetchAuctionResults } from '../api/client'
import { calcStats, groupByField, groupByMonth } from '../utils/aggregation'
import Breadcrumb from '../components/Breadcrumb'
import Sparkline from '../components/Sparkline'

export default function GenerationIndex() {
  const { modelSlug } = useParams()
  const model = ALL_MODELS.find(m => m.slug === modelSlug)
  const generations = GENERATIONS[modelSlug] ?? []
  const modelLine   = MODEL_LINE[modelSlug]

  const [results, setResults]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error,   setError]     = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchAuctionResults({ model_line: modelLine })
      .then(setResults)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [modelLine])

  const byGen = useMemo(() => groupByField(results, 'generation'), [results])

  if (!model) return <Navigate to="/" replace />

  return (
    <div className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={[
          { label: 'Markets', to: '/' },
          { label: model.label },
        ]} />
        <h1 className="page-title">{model.label}</h1>
      </div>

      {loading && <p className="status">Loading…</p>}
      {error   && <p className="status error">Error: {error}</p>}

      {!loading && !error && (
        <div className="card-grid">
          {generations.map(gen => {
            const genResults = byGen[gen] ?? []
            const stats   = calcStats(genResults)
            const monthly = groupByMonth(genResults)
            return (
              <Link key={gen} to={`/${modelSlug}/${gen}`} className="index-card">
                <div className="index-card-header">
                  <span className="index-card-name">{gen}</span>
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
