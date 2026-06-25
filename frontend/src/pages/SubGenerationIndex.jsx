import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS, MODEL_LINE, GENERATION_HERO } from '../data/taxonomy'
import { fetchAuctionResults } from '../api/client'
import { calcStats, groupByField, groupByMonth } from '../utils/aggregation'
import Breadcrumb from '../components/Breadcrumb'
import PriceHistoryChart from '../components/PriceHistoryChart'
import Sparkline from '../components/Sparkline'

const GEN_CARD_IMAGES = {
  'F-Body': '/images/911_gen_page_cards/911R(1967)Fbodygenpic.jpeg',
  'G-Body': '/images/911_gen_page_cards/930turbogbodygen.jpg',
  '964':    '/images/911_gen_page_cards/porsche964RS.png',
  '993':    '/images/911_gen_page_cards/993GT2.png',
  '996':    '/images/911_gen_page_cards/996.jpeg',
  '997':    '/images/911_gen_page_cards/997GT2.png',
  '991':    '/images/911_gen_page_cards/991gt2rs.png',
  '992':    '/images/911_gen_page_cards/911st.png',
}

const GEN_YEARS = {
  '996': '1997–2005',
  '997': '2004–2012',
  '991': '2011–2019',
  '992': '2019–present',
}

const GEN_DESCRIPTIONS = {
  '996': 'The 996 generation brought sweeping change to the 911 with the introduction of a water-cooled flat-six and an all-new body platform shared with the Boxster. It was the most affordable modern 911 at launch and significantly expanded the model\'s customer base. Today the 996 represents strong value among modern 911s, particularly in GT3, Turbo, and GT2 form.',
  '997': 'The 997 restored classic 911 design cues — most notably round headlights — while building on the water-cooled foundation of the 996. Two distinct model years split the generation into pre- and post-facelift cars, each with distinct engineering and character. GT variants in particular command strong and rising values, with the GT3 RS 4.0 widely regarded as one of the greatest driver\'s Porsches ever built.',
  '991': 'The 991 brought a longer wheelbase, wider track, and electric power steering, representing the most significant 911 evolution in a generation. It was the last 911 offered with a naturally aspirated flat-six in Carrera form before the 992 moved fully to turbocharged engines. GT3, R, and Speedster variants from this generation are already considered future classics.',
  '992': 'The 992 is the most capable and technologically advanced 911 to date, standardizing the widened body shell and twin-turbocharged flat-six across the entire Carrera range. Launched in 2019 with the 992.1 and refreshed for 2025 with the 992.2, the generation continues to evolve while maintaining the 911\'s fundamental character. GT3 and GT3 RS variants have drawn wide acclaim as the benchmark for naturally aspirated, road-legal track cars.',
}

function fmtVal(n) {
  return n ? `$${n.toLocaleString()}` : '—'
}

export default function SubGenerationIndex() {
  const { modelSlug, seg1 } = useParams()
  const model    = ALL_MODELS.find(m => m.slug === modelSlug)
  const modelLine = MODEL_LINE[modelSlug]
  const subGens  = GENERATION_GROUPS[modelSlug]?.[seg1] ?? []

  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchAuctionResults({ model_line: modelLine })
      .then(data => setResults(data.filter(r => subGens.includes(r.generation))))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [modelLine, seg1])

  const byGen      = useMemo(() => groupByField(results, 'generation'), [results])
  const heroStats  = useMemo(() => calcStats(results),    [results])
  const monthlyData = useMemo(() => groupByMonth(results), [results])
  const heroImg   = GENERATION_HERO[modelSlug]?.[seg1] ?? null

  const heroRef    = useRef(null)
  const contentRef = useRef(null)

  useEffect(() => {
    const hero    = heroRef.current
    const content = contentRef.current
    if (!hero || !content) return
    const onScroll = () => {
      const H      = hero.offsetHeight
      const belowH = document.body.scrollHeight - H
      const maxY   = document.body.scrollHeight - window.innerHeight
      const T      = maxY * 0.5
      const y      = window.scrollY

      if (y <= 0 || y >= maxY) {
        content.style.transform = ''
        return
      }

      let extra
      if (y <= T) {
        const t = y / T
        extra = t * 60
      } else {
        const t     = (y - T) / T
        const lag   = 60 * (1 - t)
        const surge = -200 * 6.75 * t * (1 - t) * (1 - t)
        extra = lag + surge
      }

      const floor = y - belowH
      if (extra < floor) extra = floor

      content.style.transform = `translateY(${extra}px)`
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (content) content.style.transform = ''
    }
  }, [])

  if (!model) return <Navigate to="/" replace />

  return (
    <>
      {heroImg && (
        <div
          ref={heroRef}
          className="gen-parallax-hero"
          style={{ backgroundImage: `url(${heroImg})` }}
        />
      )}
      <div ref={contentRef} className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={[
          { label: 'Markets',   to: '/' },
          { label: model.label, to: `/${modelSlug}` },
          { label: seg1 },
        ]} />
      </div>

      <div className="gen-hero">
        <div className="gen-hero-left">
          <div>
            <div className="gen-hero-eyebrow">Porsche {model.label}</div>
            <h1 className="gen-hero-title">{seg1}</h1>
          </div>
          {GEN_DESCRIPTIONS[seg1] && (
            <p className="gen-hero-desc">{GEN_DESCRIPTIONS[seg1]}</p>
          )}
          <div className="gen-hero-stats">
            {GEN_YEARS[seg1] && (
              <div className="gen-hero-stat">
                <span className="gen-hero-stat-label">Years</span>
                <span className="gen-hero-stat-value">{GEN_YEARS[seg1]}</span>
              </div>
            )}
            <div className="gen-hero-stat">
              <span className="gen-hero-stat-label">Avg Sale</span>
              <span className="gen-hero-stat-value">{fmtVal(heroStats.avg)}</span>
            </div>
          </div>
        </div>

        <div className="gen-hero-right">
          {GEN_CARD_IMAGES[seg1] && (
            <img
              src={GEN_CARD_IMAGES[seg1]}
              alt={`${model.label} ${seg1}`}
              className="gen-hero-img"
            />
          )}
        </div>
      </div>

      {!loading && !error && monthlyData.length >= 2 && (
        <PriceHistoryChart monthlyData={monthlyData} defaultExpanded={false} />
      )}

      {loading && <p className="status">Loading…</p>}
      {error   && <p className="status error">Error: {error}</p>}

      {!loading && !error && (
        <div className="card-grid">
          {subGens.map(subGen => {
            const genResults = byGen[subGen] ?? []
            const stats   = calcStats(genResults)
            const monthly = groupByMonth(genResults)
            return (
              <Link key={subGen} to={`/${modelSlug}/${seg1}/${subGen}`} className="index-card">
                <div className="index-card-header">
                  <span className="index-card-name">{subGen}</span>
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
    </>
  )
}
