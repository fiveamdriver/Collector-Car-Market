import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ALL_MODELS, MODEL_LINE } from '../data/taxonomy'
import { fetchModelLineStats } from '../api/client'
import porscheCrest from '../assets/Porsche_Symbol_1.png'

const MODEL_IMAGES = {
  '911':        '/images/993.jpg',
  '356':        '/images/356.jpeg',
  'cayman':     '/images/cayman-gt4.jpeg',
  'boxster':    '/images/spyder rs.webp',
  '959':        '/images/959.jpg',
  'carrera-gt': '/images/carrera gt.jpeg',
  '918-spyder': '/images/918.jpeg',
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
        <div className="model-card-body">
          <span className="model-card-name">{m.label}</span>
          {s?.count > 0 && (
            <>
              <span className="model-card-price">${s.avg.toLocaleString()}</span>
              <span className="model-card-meta">{s.count} sales · avg price</span>
            </>
          )}
        </div>
        {MODEL_IMAGES[m.slug] && (
          <img src={MODEL_IMAGES[m.slug]} alt={m.label} className="model-card-img" />
        )}
      </Link>
    )
  }

  return (
    <div className="inner">
      <div className="page-header">
        <div className="hero-columns">
          <div className="hero-col-left">
            <h1 className="page-title">Porsche</h1>
            <p className="page-desc">
              Porsche is a benchmark performance marque defined by its motorsport heritage, engineering
              excellence, and focus on driver engagement. Its appeal among enthusiasts and collectors stems
              not only from its performance credentials, but also from the nuanced evolution of its models,
              limited-production variants, and strong historical significance. Few automotive brands have
              cultivated a community as passionate and knowledgeable about provenance, specification,
              and heritage.
            </p>
          </div>
          <div className="hero-col-right">
            <img src={porscheCrest} alt="Porsche crest" className="hero-crest" />
          </div>
        </div>
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
