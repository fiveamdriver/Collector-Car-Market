import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS, GENERATIONS, GEN_LABELS, genImage, GEN_YEARS, MODEL_LINE } from '../data/taxonomy'
import { fetchAggregateStats } from '../api/client'
import { combineStats, indexByKey, statsFromGroup } from '../utils/aggregation'
import Breadcrumb from '../components/Breadcrumb'

// Models whose generation page shows photo cards before every generation has a
// photo (owner, 2026-11-12: Cayman 987 and Boxster 986 first, the rest to follow).
const PHOTO_CARDS_PARTIAL = new Set(['cayman', 'boxster'])

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
  // Photo cards when every generation has a photo, or, for models listed in
  // PHOTO_CARDS_PARTIAL, as soon as one does (the rest stay plain until their
  // photo lands). The 356 page keeps the plain layout until all four exist.
  const showPhotos = generations.length > 0 && (PHOTO_CARDS_PARTIAL.has(modelSlug)
    ? generations.some(g => genImage(modelSlug, g))
    : generations.every(g => genImage(modelSlug, g)))

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
        <div className={showPhotos ? 'card-grid card-grid--photo card-grid--gen' : 'card-grid card-grid--4col'}>
          {generations.map(gen => {
            const subGens = groups[gen]
            const stats = subGens
              ? combineStats(subGens.map(sg => byGen[sg]))
              : statsFromGroup(byGen[gen])
            const imgStyle = GEN_IMAGE_POSITION[gen] ? { objectPosition: GEN_IMAGE_POSITION[gen] } : undefined
            const photo = genImage(modelSlug, gen)
            if (showPhotos && photo) {
              // Same card as the variant pages: photo fills the card, text on top.
              return (
                <Link key={gen} to={`/${modelSlug}/${gen}`} className="index-card index-card--bg">
                  <img src={photo} alt="" className="index-card-bg-img"
                    loading="lazy" decoding="async" style={imgStyle} />
                  <div className="index-card-header">
                    <span className="index-card-name">{GEN_LABELS[gen] ?? gen}</span>
                    <span className="index-card-count">{stats.count.toLocaleString()} sold</span>
                  </div>
                  {GEN_YEARS[gen] && <span className="index-card-years">{GEN_YEARS[gen]}</span>}
                </Link>
              )
            }
            return (
              <Link key={gen} to={`/${modelSlug}/${gen}`} className="index-card">
                {photo && (
                  <div className="index-card-img-wrap">
                    <img src={photo} alt={GEN_LABELS[gen] ?? gen} className="index-card-img"
                      loading="lazy" decoding="async" style={imgStyle} />
                  </div>
                )}
                <div className="index-card-body">
                  <span className="index-card-name">{GEN_LABELS[gen] ?? gen}</span>
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
