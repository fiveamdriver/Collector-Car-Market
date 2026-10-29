import { useEffect, useMemo, useState } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, MODEL_LINE, VARIANTS, VARIANT_HERO, MODEL_HERO, VARIANT_MODELS, GROUP_CHILDREN, CROSS_LISTINGS } from '../data/taxonomy'
import VARIANT_DESCRIPTIONS, { PRODUCTION_NUMBERS, MODEL_DESCRIPTIONS, MODEL_PRODUCTION } from '../data/variantDescriptions'
import { fetchAuctionResults, fetchActiveListings } from '../api/client'
import { calcStats, groupByMonth } from '../utils/aggregation'
import { fromSlug } from '../utils/slugs'
import Breadcrumb from '../components/Breadcrumb'
import StatsBar from '../components/StatsBar'
import VariantHero from '../components/VariantHero'
import PriceHistoryChart from '../components/LazyPriceHistoryChart'
import ResultsTable from '../components/ResultsTable'
import ActiveListingsPanel from '../components/ActiveListingsPanel'

export default function MarketDetail() {
  const { modelSlug, seg1, seg2, seg3 } = useParams()
  const model     = ALL_MODELS.find(m => m.slug === modelSlug)
  const modelLine = MODEL_LINE[modelSlug]

  // variant-model (924/944/914): no generation level — seg1 is the variant.
  const isVariantModel = model?.type === 'variant-model'

  let groupSlug, generation, variantSlug
  if (isVariantModel) {
    groupSlug = null; generation = null; variantSlug = seg1 ?? null
  } else if (!seg1) {
    groupSlug = null; generation = null; variantSlug = null
  } else if (seg3) {
    groupSlug = seg1; generation = seg2; variantSlug = seg3
  } else {
    groupSlug = null; generation = seg1; variantSlug = seg2
  }

  const candidates = isVariantModel
    ? (VARIANT_MODELS[modelSlug] ?? [])
    : (VARIANTS[modelSlug]?.[generation] ?? [])
  const variant    = variantSlug ? fromSlug(variantSlug, candidates) : null

  const [tab, setTab] = useState('results')

  const [results, setResults]         = useState([])
  const [loading, setLoading]         = useState(true)
  const [error,   setError]           = useState(null)

  const [listings, setListings]               = useState([])
  const [listingsLoading, setListingsLoading] = useState(false)
  const [listingsError,   setListingsError]   = useState(null)

  // Reset listings when navigating to a different market
  useEffect(() => {
    setListings([])
    setListingsError(null)
  }, [modelLine, generation, variant])

  useEffect(() => {
    let stale = false // ignore responses that land after a navigation
    setLoading(true)
    setError(null)
    // limit must match the index pages — the API default of 500 silently
    // truncates and makes this page's stats disagree with its parent index.
    const params = { model_line: modelLine, limit: 10000 }
    if (generation) params.generation = generation
    if (variant)    params.variant    = variant
    const crossEntries = variant ? (CROSS_LISTINGS[modelSlug]?.[generation]?.[variant] ?? []) : []
    const fetches = [
      fetchAuctionResults(params),
      ...crossEntries.map(e =>
        fetchAuctionResults({ ...e.params, limit: 10000 }).then(rows =>
          rows.filter(r =>
            e.ids?.includes(r.id) ||
            (e.titlePattern != null && new RegExp(e.titlePattern, 'i').test(r.lot_title ?? ''))
          )
        )
      ),
    ]
    Promise.all(fetches)
      .then(batches => {
        if (stale) return
        const merged = batches.flat()
        merged.sort((a, b) => (b.sold_date ?? '').localeCompare(a.sold_date ?? ''))
        setResults(merged)
      })
      .catch(e => { if (!stale) setError(e.message) })
      .finally(() => { if (!stale) setLoading(false) })
    return () => { stale = true }
  }, [modelLine, modelSlug, generation, variant])

  // Fetch active listings lazily when the tab is first activated
  useEffect(() => {
    if (tab !== 'listings') return
    let stale = false
    setListingsLoading(true)
    setListingsError(null)
    const params = { model_line: modelLine }
    if (generation) params.generation = generation
    if (variant)    params.variant    = variant
    fetchActiveListings(params)
      .then(rows => { if (!stale) setListings(rows) })
      .catch(e => { if (!stale) setListingsError(e.message) })
      .finally(() => { if (!stale) setListingsLoading(false) })
    return () => { stale = true }
  }, [tab, modelLine, generation, variant])

  const stats       = useMemo(() => calcStats(results),    [results])
  const monthlyData = useMemo(() => groupByMonth(results), [results])

  if (!model) return <Navigate to="/" replace />

  // Show the hero panel on terminal pages: a specific variant, or a standalone model
  const showHero = variant !== null || model.type === 'standalone'
  const heroFile  = variant
    ? (VARIANT_HERO[modelSlug]?.[generation]?.[variant] ?? null)
    : (MODEL_HERO[modelSlug] ?? null)
  // Entries are bare filenames resolved against /images/variants/, but an entry
  // may also give a full path when the image lives elsewhere (the restomod cards
  // reuse their front-page photo rather than duplicating a 300KB file).
  const heroImage = heroFile
    ? (heroFile.startsWith('/') ? heroFile : `/images/variants/${heroFile}`)
    : null

  // Eyebrow: "Porsche 911 · 993" or "Porsche 959" etc. Coachbuilders are not
  // Porsche models — "Porsche Singer" reads wrong — so they're labelled by what
  // they are instead.
  const eyebrow = model.category === 'restomod'
    ? 'Restomod'
    : generation
      ? `Porsche ${model.label} · ${generation}`
      : `Porsche ${model.label}`

  // Hero title: 911 pages show the variant alone ("Carrera RS 2.7") — the
  // eyebrow already carries the generation. Others: "718 GT4", "944 Turbo",
  // or the standalone model name.
  const heroTitle = variant
    ? (isVariantModel
        ? (variant === 'base' || variant.includes(model.label)
            ? (variant === 'base' ? model.label : variant)
            : `${model.label} ${variant}`)
        : (modelSlug === '911' || modelSlug === '911-race')
            ? variant
            : `${generation} ${variant}`)
    : model.label

  // Three shapes of market page, three places the hero copy and production
  // count live: variant-models (924/944/968/928/914) have no generation level
  // and are keyed [modelSlug][variant]; standalone models (959, Carrera GT,
  // the coachbuilders, the race cars) have neither and are keyed [modelSlug].
  const description = variant
    ? (isVariantModel
        ? VARIANT_DESCRIPTIONS[modelSlug]?.[variant]
        : VARIANT_DESCRIPTIONS[modelSlug]?.[generation]?.[variant]) ?? null
    : (MODEL_DESCRIPTIONS[modelSlug] ?? null)

  const productionCount = variant
    ? (isVariantModel
        ? PRODUCTION_NUMBERS[modelSlug]?.[variant]
        : PRODUCTION_NUMBERS[generation]?.[variant]) ?? null
    : (MODEL_PRODUCTION[modelSlug] ?? null)

  const crumbs = [{ label: 'Markets', to: '/' }]
  if (model.type === 'series') {
    crumbs.push({ label: model.label, to: `/${modelSlug}` })
    if (groupSlug)  crumbs.push({ label: groupSlug,  to: `/${modelSlug}/${groupSlug}` })
    if (generation) crumbs.push({ label: generation, to: groupSlug
      ? `/${modelSlug}/${groupSlug}/${generation}`
      : `/${modelSlug}/${generation}` })
    if (variant)    crumbs.push({ label: variant })
  } else if (isVariantModel) {
    const parentSlug = Object.keys(GROUP_CHILDREN).find(g => GROUP_CHILDREN[g].includes(modelSlug))
    if (parentSlug) {
      const parent = ALL_MODELS.find(m => m.slug === parentSlug)
      crumbs.push({ label: parent?.label ?? parentSlug, to: `/${parentSlug}` })
    }
    crumbs.push({ label: model.label, to: `/${modelSlug}` })
    if (variant) crumbs.push({ label: variant === 'base' ? model.label : variant })
  } else {
    crumbs.push({ label: model.label })
  }

  const title = [model.label, generation, variant].filter(Boolean).join(' ')

  return (
    <div className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={crumbs} />
        {!showHero && <h1 className="page-title">{title}</h1>}
      </div>

      <div className="tabs">
        <button
          className={`tab-btn${tab === 'results' ? ' active' : ''}`}
          onClick={() => setTab('results')}
        >
          Auction Results
        </button>
        <button
          className={`tab-btn${tab === 'listings' ? ' active' : ''}`}
          onClick={() => setTab('listings')}
        >
          Active Listings
        </button>
      </div>

      {tab === 'results' && (
        <>
          {loading && <p className="status">Loading…</p>}
          {error   && <p className="status error">Error: {error}</p>}
          {!loading && !error && (
            <>
              {showHero
                ? <VariantHero
                    eyebrow={eyebrow}
                    title={heroTitle}
                    stats={stats}
                    heroImage={heroImage}
                    description={description}
                    productionCount={productionCount}
                  />
                : <StatsBar {...stats} />}
              {monthlyData.length >= 2 && (
                <PriceHistoryChart monthlyData={monthlyData} />
              )}
              <ResultsTable results={results} />
            </>
          )}
        </>
      )}

      {tab === 'listings' && (
        <ActiveListingsPanel
          listings={listings}
          loading={listingsLoading}
          error={listingsError}
        />
      )}
    </div>
  )
}
