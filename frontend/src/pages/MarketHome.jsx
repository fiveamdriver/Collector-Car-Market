import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ALL_MODELS, MODEL_LINE, GROUP_CHILDREN } from '../data/taxonomy'
import { fetchModelLineStats } from '../api/client'

// Drives both the side nav and the sections themselves, so the two can't drift.
const SECTIONS = [
  { id: 'model-lines', label: 'Model Lines',      category: 'series' },
  { id: 'specialty',   label: 'Specialty Models', category: 'specialty' },
  { id: 'race',        label: 'Race Cars',        category: 'race' },
  { id: 'restomods',   label: 'Restomods',        category: 'restomod' },
]

const MODEL_YEARS = {
  '911':        '1963–present',
  '356':        '1948–1965',
  'transaxle':  '1976–1995',
  'cayman':     '2005–present',
  'boxster':    '1996–present',
  '914':        '1969–1976',
  '959':        '1986–1988',
  'carrera-gt': '2004–2006',
  '918-spyder': '2013–2015',
  'singer':        '2009–present',
  'gunther-werks': '2017–present',
  'emory':         '1996–present',
  '911-race':   '1973–present',
  '911-gt1':    '1996–1998',
  '917':        '1969–1973',
  '956':        '1982–1985',
  '962':        '1984–1991',
  '935':        '1976–1981',
  '934':        '1976–1979',
  '908':        '1968–1971',
  '907':        '1967–1968',
  '906':        '1966–1967',
  '904':        '1963–1965',
  '550':        '1953–1956',
  'rs60':       '1960–1961',
  '718-rsk':    '1957–1960',
  'rs-spyder':  '2005–2010',
}

const IMAGE_POSITION = {
  'cayman': 'center bottom',
}


const MODEL_IMAGES = {
  '911':        '/images/Front_page_cards/Regular_models/997RS4.0v2.png',
  '356':        '/images/Front_page_cards/Regular_models/356(frontpage).png',
  'transaxle':  '/images/Front_page_cards/Regular_models/924_CarreraGT.png',
  'cayman':     '/images/Front_page_cards/Regular_models/GT4RS.png',
  'boxster':    '/images/Front_page_cards/Regular_models/spyderrsfront.png',
  '914':        '/images/Front_page_cards/Regular_models/porsche 914.jpg',
  '959':        '/images/Front_page_cards/Specialty/959hero.jpg',
  'carrera-gt': '/images/Front_page_cards/Specialty/cgthero.jpeg',
  '918-spyder': '/images/Front_page_cards/Specialty/918hero.png',
  'singer':        '/images/Front_page_cards/Restomod/singer_dls.jpg',
  'gunther-werks': '/images/Front_page_cards/Restomod/gunther_werks_f26.jpg',
  'emory':         '/images/Front_page_cards/Restomod/emory_motorsports.jpg',
  '911-race':   '/images/Front_page_cards/Racecars/RSR.jpg',
  '911-gt1':    '/images/Front_page_cards/Racecars/gt1.png',
  '917':        '/images/Front_page_cards/Racecars/917.png',
  '956':        '/images/Front_page_cards/Racecars/956.jpg',
  '962':        '/images/Front_page_cards/Racecars/962.png',
  '935':        '/images/Front_page_cards/Racecars/935.png',
  '934':        '/images/Front_page_cards/Racecars/934.png',
  '908':        '/images/Front_page_cards/Racecars/908.jpg',
  '907':        '/images/Front_page_cards/Racecars/907.png',
  '906':        '/images/Front_page_cards/Racecars/906.jpg',
  '904':        '/images/Front_page_cards/Racecars/904.jpg',
  '550':        '/images/Front_page_cards/Racecars/550 spyder.jpg',
  'rs60':       '/images/Front_page_cards/Racecars/RS60.jpg',
  '718-rsk':    '/images/Front_page_cards/Racecars/RSK.jpg',
  'rs-spyder':  '/images/Front_page_cards/Racecars/RS spyder (racecar).jpg',
}

// Top-level so React reconciles cards across renders instead of remounting
// them (a component defined inside the render body is a new element type on
// every render, which destroys and recreates all 24 card images when the
// stats response lands).
function ModelCard({ m, stats }) {
  return (
    <Link to={`/${m.slug}`} className="model-card">
      {MODEL_IMAGES[m.slug] && (
        <img src={MODEL_IMAGES[m.slug]} alt={m.label} className="model-card-img"
          loading="lazy" decoding="async"
          style={IMAGE_POSITION[m.slug] ? { objectPosition: IMAGE_POSITION[m.slug] } : undefined} />
      )}
      <div className="model-card-body">
        <span className="model-card-name">{m.label}</span>
        {MODEL_YEARS[m.slug] && (
          <span className="model-card-years">{MODEL_YEARS[m.slug]}</span>
        )}
        {stats?.count > 0 && stats.avg > 0 && (
          <>
            <span className="model-card-price">${stats.avg.toLocaleString()} <span className="model-card-price-label">avg price</span></span>
            <span className="model-card-meta">{stats.count.toLocaleString()} results</span>
          </>
        )}
      </div>
    </Link>
  )
}

export default function MarketHome() {
  const [modelStats, setModelStats] = useState({})
  const [statsError, setStatsError] = useState(null)
  const [activeId, setActiveId]     = useState(SECTIONS[0].id)
  const sectionRefs = useRef({})

  // The active section is the last one whose top has scrolled past the marker —
  // not the one nearest to it, which lights up the *next* section while you're
  // still reading the current one.
  useEffect(() => {
    const nodes = SECTIONS.map(s => sectionRefs.current[s.id]).filter(Boolean)
    if (!nodes.length) return

    const pick = () => {
      const marker = 120
      let current = nodes[0]
      for (const node of nodes) {
        if (node.getBoundingClientRect().top <= marker) current = node
      }
      // At the very bottom the last section may be too short to reach the
      // marker; it's still the one in view.
      const atBottom =
        window.innerHeight + window.scrollY >= document.body.scrollHeight - 2
      if (atBottom) current = nodes[nodes.length - 1]
      setActiveId(current.dataset.sectionId)
    }

    pick()
    window.addEventListener('scroll', pick, { passive: true })
    window.addEventListener('resize', pick)
    return () => {
      window.removeEventListener('scroll', pick)
      window.removeEventListener('resize', pick)
    }
  }, [])

  useEffect(() => {
    document.body.classList.add('theme-light')
    return () => document.body.classList.remove('theme-light')
  }, [])

  useEffect(() => {
    let stale = false
    fetchModelLineStats().then(rows => {
      if (stale) return
      const byML = Object.fromEntries(rows.map(r => [r.model_line, r]))
      const statFor = (slug) => {
        // "group" models (Transaxle) aggregate several DB model lines.
        const children = GROUP_CHILDREN[slug]
        if (children) {
          const parts = children.map(c => byML[MODEL_LINE[c]]).filter(Boolean)
          const count = parts.reduce((n, r) => n + r.count, 0)
          // Weight each line's average by its priced-row count and skip
          // lines with no priced rows — weighting by the all-rows count
          // biased the blend, and a null average contributed 0 to the
          // numerator while still counting in the denominator.
          const priced = parts.filter(r => r.avg_sold_price != null)
          const pricedCount = priced.reduce((n, r) => n + r.priced_count, 0)
          const avg = pricedCount
            ? Math.round(priced.reduce((s, r) => s + r.avg_sold_price * r.priced_count, 0) / pricedCount)
            : 0
          return { count, avg }
        }
        return { count: byML[MODEL_LINE[slug]]?.count ?? 0, avg: byML[MODEL_LINE[slug]]?.avg_sold_price ?? 0 }
      }
      setModelStats(Object.fromEntries(ALL_MODELS.map(m => [m.slug, statFor(m.slug)])))
    }).catch(err => { if (!stale) setStatsError(err.message) })
    return () => { stale = true }
  }, [])

  const scrollTo = (id) => (e) => {
    e.preventDefault()
    sectionRefs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setActiveId(id)
  }

  return (
    <div className="inner home">
      {/* Sits in its own grid row above both columns, so the nav lines up with
          the first section heading rather than with the page title. */}
      <div className="page-header home-header">
        <h1 className="page-title">Porsche</h1>
      </div>

      <nav className="home-nav" aria-label="Categories">
        <ul className="home-nav-list">
          {SECTIONS.map(s => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                className={`home-nav-item${activeId === s.id ? ' is-active' : ''}`}
                aria-current={activeId === s.id ? 'true' : undefined}
                onClick={scrollTo(s.id)}
              >
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="home-main">
        {statsError && <p className="status error">Could not load market stats: {statsError}</p>}

        {SECTIONS.map(s => (
          <section
            key={s.id}
            id={s.id}
            data-section-id={s.id}
            ref={el => { sectionRefs.current[s.id] = el }}
            className="section"
          >
            <h2 className="section-label">{s.label}</h2>
            <div className="card-grid card-grid--models">
              {ALL_MODELS.filter(m => m.category === s.category).map(m => (
                <ModelCard key={m.slug} m={m} stats={modelStats[m.slug]} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
