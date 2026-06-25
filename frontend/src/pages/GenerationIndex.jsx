import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS, GENERATIONS, MODEL_LINE } from '../data/taxonomy'
import { fetchAuctionResults } from '../api/client'
import { calcStats, groupByField } from '../utils/aggregation'
import Breadcrumb from '../components/Breadcrumb'

const GEN_IMAGES = {
  'F-Body': '/images/911_gen_page_cards/911R(1967)Fbodygenpic.jpeg',
  'G-Body': '/images/911_gen_page_cards/930turbogbodygen.jpg',
  '964':    '/images/911_gen_page_cards/porsche964RS.png',
  '993':    '/images/911_gen_page_cards/993GT2.png',
  '996':    '/images/911_gen_page_cards/996.jpeg',
  '997':    '/images/911_gen_page_cards/997GT2.png',
  '991':    '/images/911_gen_page_cards/991gt2rs.png',
  '992':    '/images/911_gen_page_cards/911st.png',
}

const GEN_IMAGE_POSITION = {
  'G-Body': 'center bottom',
  '992':    '28% center',
}

const GEN_IMAGE_TRANSFORM = {}

const GEN_YEARS = {
  'F-Body': '1963–1973',
  'G-Body': '1974–1989',
  '964':    '1989–1994',
  '993':    '1994–1998',
  '996':    '1997–2005',
  '997':    '2004–2012',
  '991':    '2011–2019',
  '992':    '2019–present',
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
                      style={{
                        ...(GEN_IMAGE_POSITION[gen] ? { objectPosition: GEN_IMAGE_POSITION[gen] } : {}),
                        ...(GEN_IMAGE_TRANSFORM[gen] ? { transform: GEN_IMAGE_TRANSFORM[gen] } : {}),
                      }} />
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
