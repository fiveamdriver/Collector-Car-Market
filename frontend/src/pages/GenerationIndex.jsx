import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS, GENERATIONS, GEN_IMAGES, GEN_YEARS, MODEL_LINE } from '../data/taxonomy'
import { fetchAuctionResults } from '../api/client'
import { calcStats, groupByField } from '../utils/aggregation'
import Breadcrumb from '../components/Breadcrumb'

const GEN_IMAGE_POSITION = {
  'G-Body': 'center bottom',
  '992':    '28% center',
}

export default function GenerationIndex() {
  const { modelSlug } = useParams()
  const model      = ALL_MODELS.find(m => m.slug === modelSlug)
  const generations = GENERATIONS[modelSlug] ?? []
  const modelLine  = MODEL_LINE[modelSlug]
  const groups     = GENERATION_GROUPS[modelSlug] ?? {}

  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchAuctionResults({ model_line: modelLine, limit: 10000 })
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
        <div className="card-grid card-grid--4col">
          {generations.map(gen => {
            const subGens    = groups[gen]
            const genResults = subGens
              ? subGens.flatMap(sg => byGen[sg] ?? [])
              : (byGen[gen] ?? [])
            const stats = calcStats(genResults)
            return (
              <Link key={gen} to={`/${modelSlug}/${gen}`} className="index-card">
                {GEN_IMAGES[gen] && (
                  <div className="index-card-img-wrap">
                    <img src={GEN_IMAGES[gen]} alt={gen} className="index-card-img"
                      style={GEN_IMAGE_POSITION[gen] ? { objectPosition: GEN_IMAGE_POSITION[gen] } : undefined} />
                  </div>
                )}
                <div className="index-card-body">
                  <span className="index-card-name">{gen}</span>
                  {GEN_YEARS[gen] && (
                    <span className="index-card-years">{GEN_YEARS[gen]}</span>
                  )}
                  {stats.count > 0 && (
                    <>
                      <span className="index-card-price">${stats.avg.toLocaleString()} <span className="index-card-price-label">avg price</span></span>
                      <span className="index-card-count">{stats.count.toLocaleString()} sold</span>
                    </>
                  )}
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
