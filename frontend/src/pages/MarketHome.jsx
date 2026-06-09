import { Link } from 'react-router-dom'
import { ALL_MODELS } from '../data/taxonomy'

export default function MarketHome() {
  const series     = ALL_MODELS.filter(m => m.type === 'series')
  const standalone = ALL_MODELS.filter(m => m.type === 'standalone')

  return (
    <div className="inner">
      <div className="page-header">
        <h1 className="page-title">Markets</h1>
        <p className="page-subtitle">Porsche auction results and price trends</p>
      </div>

      <section className="section">
        <h2 className="section-label">Model Lines</h2>
        <div className="card-grid">
          {series.map(m => (
            <Link key={m.slug} to={`/${m.slug}`} className="model-card">
              <span className="model-card-name">{m.label}</span>
              <span className="model-card-sub">View generations →</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <h2 className="section-label">Specialty Models</h2>
        <div className="card-grid">
          {standalone.map(m => (
            <Link key={m.slug} to={`/${m.slug}`} className="model-card">
              <span className="model-card-name">{m.label}</span>
              <span className="model-card-sub">View results →</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
