function fmt(n) {
  return n ? `$${n.toLocaleString()}` : '—'
}

export default function VariantHero({ eyebrow, title, subtitle, description, stats, heroImage, productionCount }) {
  const { avg } = stats

  return (
    <div className={`variant-hero${heroImage ? ' variant-hero--photo' : ''}`}>
      <div className="variant-hero-left">
        <div className="variant-hero-text">
          {eyebrow && <div className="variant-hero-eyebrow">{eyebrow}</div>}
          <h1 className="variant-hero-title">{title}</h1>
          {subtitle && <div className="variant-hero-subtitle">{subtitle}</div>}
        </div>
        {description && <p className="gen-hero-desc">{description}</p>}
        <div className="variant-hero-stats">
          {productionCount != null && (
            <div className="vh-stat">
              <span className="vh-stat-label">No. of Examples</span>
              <span className="vh-stat-value">{productionCount.toLocaleString()}</span>
            </div>
          )}
          <div className="vh-stat">
            <span className="vh-stat-label">Avg Sale</span>
            <span className="vh-stat-value">{fmt(avg)}</span>
          </div>
        </div>
      </div>

      <div className="variant-hero-right">
        {heroImage
          ? <img src={heroImage} alt={title} className="variant-hero-img" />
          : <div className="variant-hero-placeholder" />}
      </div>
    </div>
  )
}
