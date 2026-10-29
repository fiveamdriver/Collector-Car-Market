import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, MODEL_LINE, VARIANT_MODELS, TRANSAXLE_META, GROUP_CHILDREN } from '../data/taxonomy'
import { fetchAggregateStats } from '../api/client'
import { indexByKey, statsFromGroup, toMonthlySeries } from '../utils/aggregation'
import { toSlug } from '../utils/slugs'
import { variantLabel } from '../utils/variantLabel'
import Breadcrumb from '../components/Breadcrumb'
import Sparkline from '../components/Sparkline'

// A "variant-model" (e.g. 924, 944, 914) splits into trim cards — like a 911
// generation splits into variants — but with no generation level in between.
export default function VariantModelIndex() {
  const { modelSlug } = useParams()
  const model     = ALL_MODELS.find(m => m.slug === modelSlug)
  const modelLine = MODEL_LINE[modelSlug]
  const variants  = VARIANT_MODELS[modelSlug] ?? []
  const meta      = TRANSAXLE_META[modelSlug] ?? {}

  // Which group (if any) this model belongs to, for the breadcrumb trail.
  const parentSlug = Object.keys(GROUP_CHILDREN).find(g => GROUP_CHILDREN[g].includes(modelSlug))

  const [groupStats, setGroupStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    let stale = false // ignore responses that land after a navigation
    setLoading(true)
    setError(null)
    fetchAggregateStats({ model_line: modelLine, group_by: 'variant', monthly: true })
      .then(data => { if (!stale) setGroupStats(data) })
      .catch(e => { if (!stale) setError(e.message) })
      .finally(() => { if (!stale) setLoading(false) })
    return () => { stale = true }
  }, [modelLine])

  const byVariant = useMemo(() => indexByKey(groupStats), [groupStats])
  const sorted = useMemo(() => (
    [...variants].sort((a, b) =>
      statsFromGroup(byVariant[b]).avg - statsFromGroup(byVariant[a]).avg)
  ), [variants, byVariant])

  if (!model) return <Navigate to="/" replace />

  const crumbs = [{ label: 'Markets', to: '/' }]
  if (parentSlug) {
    const parent = ALL_MODELS.find(m => m.slug === parentSlug)
    crumbs.push({ label: parent?.label ?? parentSlug, to: `/${parentSlug}` })
  }
  crumbs.push({ label: model.label })

  return (
    <div className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={crumbs} />
        <h1 className="page-title">{model.label}</h1>
        {meta.years && <p className="page-subtitle">{meta.years}</p>}
      </div>

      {loading && <p className="status">Loading…</p>}
      {error   && <p className="status error">Error: {error}</p>}

      {!loading && !error && (
        <div className="card-grid">
          {sorted.map(variant => {
            const group   = byVariant[variant]
            const stats   = statsFromGroup(group)
            const monthly = toMonthlySeries(group?.monthly)
            const label   = variantLabel(model, variant)
            return (
              <Link key={variant} to={`/${modelSlug}/${toSlug(variant)}`} className="index-card">
                <div className="index-card-header">
                  <span className="index-card-name">{label}</span>
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
