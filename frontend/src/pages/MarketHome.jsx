import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ALL_MODELS, MODEL_LINE } from '../data/taxonomy'
import { fetchModelLineStats } from '../api/client'

const MODEL_YEARS = {
  '911':        '1963–present',
  '356':        '1948–1965',
  'cayman':     '2005–present',
  'boxster':    '1996–present',
  '959':        '1986–1988',
  'carrera-gt': '2004–2006',
  '918-spyder': '2013–2015',
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
  'cayman':     '/images/Front_page_cards/Regular_models/GT4RS.png',
  'boxster':    '/images/Front_page_cards/Regular_models/spyderrsfront.png',
  '959':        '/images/Front_page_cards/Specialty/959hero.jpg',
  'carrera-gt': '/images/Front_page_cards/Specialty/cgthero.jpeg',
  '918-spyder': '/images/Front_page_cards/Specialty/918hero.png',
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

export default function MarketHome() {
  const series     = ALL_MODELS.filter(m => m.category === 'series')
  const standalone = ALL_MODELS.filter(m => m.category === 'specialty')
  const race       = ALL_MODELS.filter(m => m.category === 'race')

  const [modelStats, setModelStats] = useState({})
  const [statsError, setStatsError] = useState(null)

  useEffect(() => {
    document.body.classList.add('theme-light')
    return () => document.body.classList.remove('theme-light')
  }, [])

  useEffect(() => {
    fetchModelLineStats().then(rows => {
      const byML = Object.fromEntries(rows.map(r => [r.model_line, r]))
      setModelStats(
        Object.fromEntries(
          ALL_MODELS.map(m => [
            m.slug,
            { count: byML[MODEL_LINE[m.slug]]?.count ?? 0, avg: byML[MODEL_LINE[m.slug]]?.avg_sold_price ?? 0 },
          ])
        )
      )
    }).catch(err => setStatsError(err.message))
  }, [])

  const ModelCard = ({ m }) => {
    const s = modelStats[m.slug]
    return (
      <Link key={m.slug} to={`/${m.slug}`} className="model-card">
        {MODEL_IMAGES[m.slug] && (
          <img src={MODEL_IMAGES[m.slug]} alt={m.label} className="model-card-img"
            style={IMAGE_POSITION[m.slug] ? { objectPosition: IMAGE_POSITION[m.slug] } : undefined} />
        )}
        <div className="model-card-body">
          <span className="model-card-name">{m.label}</span>
          {MODEL_YEARS[m.slug] && (
            <span className="model-card-years">{MODEL_YEARS[m.slug]}</span>
          )}
          {s?.count > 0 && (
            <>
              <span className="model-card-price">${s.avg.toLocaleString()} <span className="model-card-price-label">avg price</span></span>
              <span className="model-card-meta">{s.count.toLocaleString()} results</span>
            </>
          )}
        </div>
      </Link>
    )
  }

  return (
    <div className="inner">
      <div className="page-header">
        <h1 className="page-title">Porsche</h1>
      </div>
      {statsError && <p className="status error">Could not load market stats: {statsError}</p>}

      <section className="section">
        <h2 className="section-label">Model Lines</h2>
        <div className="card-grid card-grid--models-2col">
          {series.map(m => <ModelCard key={m.slug} m={m} />)}
        </div>
      </section>

      <section className="section">
        <h2 className="section-label">Specialty Models</h2>
        <div className="card-grid card-grid--models">
          {standalone.map(m => <ModelCard key={m.slug} m={m} />)}
        </div>
      </section>

      <section className="section">
        <h2 className="section-label">Race Cars</h2>
        <div className="card-grid card-grid--models">
          {race.map(m => <ModelCard key={m.slug} m={m} />)}
        </div>
      </section>
    </div>
  )
}
