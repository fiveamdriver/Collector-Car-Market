import { useEffect, useMemo, useState } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS, MODEL_LINE, VARIANTS, VARIANT_HERO, MODEL_HERO } from '../data/taxonomy'
import VARIANT_DESCRIPTIONS, { PRODUCTION_NUMBERS } from '../data/variantDescriptions'
import { fetchAuctionResults, fetchActiveListings } from '../api/client'
import { calcStats, groupByMonth } from '../utils/aggregation'
import { fromSlug } from '../utils/slugs'
import Breadcrumb from '../components/Breadcrumb'
import StatsBar from '../components/StatsBar'
import VariantHero from '../components/VariantHero'
import PriceHistoryChart from '../components/PriceHistoryChart'
import ResultsTable from '../components/ResultsTable'
import ActiveListingsPanel from '../components/ActiveListingsPanel'

export default function MarketDetail() {
  const { modelSlug, seg1, seg2, seg3 } = useParams()
  const model     = ALL_MODELS.find(m => m.slug === modelSlug)
  const modelLine = MODEL_LINE[modelSlug]
  const groups    = GENERATION_GROUPS[modelSlug] ?? {}

  let groupSlug, generation, variantSlug
  if (!seg1) {
    groupSlug = null; generation = null; variantSlug = null
  } else if (seg3) {
    groupSlug = seg1; generation = seg2; variantSlug = seg3
  } else {
    groupSlug = null; generation = seg1; variantSlug = seg2
  }

  const candidates = VARIANTS[modelSlug]?.[generation] ?? []
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

  // Fetch active listings lazily when the tab is first activated
  useEffect(() => {
    if (tab !== 'listings') return
    setListingsLoading(true)
    setListingsError(null)
    const params = { model_line: modelLine }
    if (generation) params.generation = generation
    if (variant)    params.variant    = variant
    fetchActiveListings(params)
      .then(setListings)
      .catch(e => setListingsError(e.message))
      .finally(() => setListingsLoading(false))
  }, [tab, modelLine, generation, variant])

  const stats       = useMemo(() => calcStats(results),    [results])
  const monthlyData = useMemo(() => groupByMonth(results), [results])

  if (!model) return <Navigate to="/" replace />

  // Show the hero panel on terminal pages: a specific variant, or a standalone model
  const showHero = variant !== null || model.type === 'standalone'
  const heroFile  = variant
    ? (VARIANT_HERO[modelSlug]?.[generation]?.[variant] ?? null)
    : (MODEL_HERO[modelSlug] ?? null)
  const heroImage = heroFile ? `/images/variants/${heroFile}` : null

  // Eyebrow: "Porsche 911 · 993" or "Porsche 959" etc.
  const eyebrow = generation
    ? `Porsche ${model.label} · ${generation}`
    : `Porsche ${model.label}`

  // Hero title: "993 GT2", "F-Body 911R", or standalone model name
  const heroTitle = variant
    ? `${generation} ${variant}`
    : model.label

  const crumbs = [{ label: 'Markets', to: '/' }]
  if (model.type === 'series') {
    crumbs.push({ label: model.label, to: `/${modelSlug}` })
    if (groupSlug)  crumbs.push({ label: groupSlug,  to: `/${modelSlug}/${groupSlug}` })
    if (generation) crumbs.push({ label: generation, to: groupSlug
      ? `/${modelSlug}/${groupSlug}/${generation}`
      : `/${modelSlug}/${generation}` })
    if (variant)    crumbs.push({ label: variant })
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
                    description={variant ? VARIANT_DESCRIPTIONS[modelSlug]?.[generation]?.[variant] : null}
                    productionCount={variant ? (PRODUCTION_NUMBERS[generation]?.[variant] ?? null) : null}
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
