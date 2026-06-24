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
  '911':        '/images/997RS4.0v2.png',
  '356':        '/images/356(frontpage).png',
  'cayman':     '/images/GT4RS.png',
  'boxster':    '/images/spyderrsfront.png',
  '959':        '/images/959hero.jpg',
  'carrera-gt': '/images/cgthero.jpeg',
  '918-spyder': '/images/918hero.png',
  '911-race':   '/images/RSR.jpg',
  '911-gt1':    '/images/gt1.png',
  '917':        '/images/917.png',
  '956':        '/images/956.jpg',
  '962':        '/images/962.png',
  '935':        '/images/935.png',
  '934':        '/images/934.png',
  '908':        '/images/908.jpg',
  '907':        '/images/907.png',
  '906':        '/images/906.jpg',
  '904':        '/images/904.jpg',
  '550':        '/images/550 spyder.jpg',
  'rs60':       '/images/RS60.jpg',
  '718-rsk':    '/images/RSK.jpg',
  'rs-spyder':  '/images/RS spyder (racecar).jpg',
}

export default function MarketHome() {
  const series     = ALL_MODELS.filter(m => m.category === 'series')
  const standalone = ALL_MODELS.filter(m => m.category === 'specialty')
  const race       = ALL_MODELS.filter(m => m.category === 'race')

  const [modelStats, setModelStats] = useState({})

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
    }).catch(err => console.error('Failed to load model line stats:', err))
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
