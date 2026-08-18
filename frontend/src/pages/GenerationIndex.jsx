import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS, GENERATIONS, GEN_IMAGES, GEN_YEARS, MODEL_LINE } from '../data/taxonomy'
import { fetchAggregateStats } from '../api/client'
import { combineStats, indexByKey, statsFromGroup } from '../utils/aggregation'
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

  const [groupStats, setGroupStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    let stale = false // ignore responses that land after a navigation
    setLoading(true)
    setError(null)
    fetchAggregateStats({ model_line: modelLine, group_by: 'generation' })
      .then(data => { if (!stale) setGroupStats(data) })
      .catch(e => { if (!stale) setError(e.message) })
      .finally(() => { if (!stale) setLoading(false) })
    return () => { stale = true }
  }, [modelLine])

  const byGen = useMemo(() => indexByKey(groupStats), [groupStats])

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
            const subGens = groups[gen]
            const stats = subGens
              ? combineStats(subGens.map(sg => byGen[sg]))
              : statsFromGroup(byGen[gen])
            return (
              <Link key={gen} to={`/${modelSlug}/${gen}`} className="index-card">
                {GEN_IMAGES[gen] && (
                  <div className="index-card-img-wrap">
                    <img src={GEN_IMAGES[gen]} alt={gen} className="index-card-img"
                      loading="lazy" decoding="async"
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
