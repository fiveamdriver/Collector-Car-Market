import { useEffect, useMemo, useState } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, MODEL_LINE, VARIANTS } from '../data/taxonomy'
import { fetchAuctionResults } from '../api/client'
import { calcStats, groupByMonth } from '../utils/aggregation'
import { fromSlug } from '../utils/slugs'
import Breadcrumb from '../components/Breadcrumb'
import StatsBar from '../components/StatsBar'
import PriceHistoryChart from '../components/PriceHistoryChart'
import ResultsTable from '../components/ResultsTable'

export default function MarketDetail() {
  const { modelSlug, generation, variantSlug } = useParams()
  const model     = ALL_MODELS.find(m => m.slug === modelSlug)
  const modelLine = MODEL_LINE[modelSlug]
  const candidates = VARIANTS[modelSlug]?.[generation] ?? []
  const variant   = variantSlug ? fromSlug(variantSlug, candidates) : null

  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = { model_line: modelLine }
    if (generation) params.generation = generation
    if (variant)    params.variant    = variant
    fetchAuctionResults(params)
      .then(setResults)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [modelLine, generation, variant])

  const stats       = useMemo(() => calcStats(results),      [results])
  const monthlyData = useMemo(() => groupByMonth(results),   [results])

  if (!model) return <Navigate to="/" replace />

  // Build breadcrumbs depending on how deep the URL is
  const crumbs = [{ label: 'Markets', to: '/' }]
  if (model.type === 'series') {
    crumbs.push({ label: model.label, to: `/${modelSlug}` })
    if (generation) crumbs.push({ label: generation, to: `/${modelSlug}/${generation}` })
    if (variant)    crumbs.push({ label: variant })
  } else {
    crumbs.push({ label: model.label })
  }

  const title = [model.label, generation, variant].filter(Boolean).join(' ')

  return (
    <div className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={crumbs} />
        <h1 className="page-title">{title}</h1>
      </div>

      {loading && <p className="status">Loading…</p>}
      {error   && <p className="status error">Error: {error}</p>}

      {!loading && !error && (
        <>
          <StatsBar {...stats} />
          {monthlyData.length >= 2 && (
            <PriceHistoryChart monthlyData={monthlyData} />
          )}
          <ResultsTable results={results} />
        </>
      )}
    </div>
  )
}
