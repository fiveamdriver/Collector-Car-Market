import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, Navigate } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS, GEN_IMAGES, GEN_YEARS, MODEL_LINE, VARIANTS, CROSS_LISTINGS } from '../data/taxonomy'
import { fetchAggregateStats, fetchAuctionResults } from '../api/client'
import {
  combineStats, groupStatsFromRows, indexByKey, mergeGroups,
  statsFromGroup, toMonthlySeries,
} from '../utils/aggregation'
import { toSlug } from '../utils/slugs'
import { variantLabel } from '../utils/variantLabel'
import Breadcrumb from '../components/Breadcrumb'
import Sparkline from '../components/Sparkline'
import { fmtVal } from '../utils/formatters'

const GEN_DESCRIPTIONS = {
  '356 A': 'Introduced at the 1955 Frankfurt show, the 356 A brought a curved one-piece windshield, softer suspension, and the larger 1600 flat-four that made the car markedly more usable. It was also the first 356 offered with the exotic four-cam Carrera engine, while the stripped-down Speedster became an icon of 1950s sports car culture. Speedsters and Carrera-engined cars rank among the most valuable 356s at auction.',
  'F-Body': 'The F-Body 911, produced from 1963 to 1973, is the original air-cooled sports car that defined Porsche\'s identity for decades. Early cars are prized for their pure, lightweight character and direct connection to Ferdinand Piëch\'s original vision. Rare variants like the Carrera RS 2.7 and 911R are among the most valuable Porsches ever sold at auction.',
  'G-Body': 'The G-Body generation ran from 1974 to 1989, the longest production run of any 911, and introduced the iconic impact bumpers that define its silhouette. It encompassed the 2.7, 3.0, and 3.2 Carrera engines, culminating in one of the finest air-cooled motors Porsche ever built. The 930 Turbo and limited Speedster variants from this era are especially sought after by collectors.',
  '964':   'Produced from 1989 to 1994, the 964 was the 911\'s first major redesign in over two decades, introducing all-wheel drive, power steering, and ABS. It retained the iconic air-cooled flat-six that defined the 911\'s character. The 964 remains one of the most collectible air-cooled Porsches, with values that have climbed steadily among enthusiasts and collectors.',
  '993':   'The 993 was the last air-cooled 911, produced from 1994 to 1998, and is widely regarded as the pinnacle of the classic 911 lineage. It introduced fully independent rear suspension and a sleeker body that remains one of the most admired 911 silhouettes. Demand has risen sharply as collectors pursue the last of the air-cooled era.',
  '996.1': 'The 996 marked a radical departure for the 911, introducing the first water-cooled engine alongside a ground-up redesign. Early 996.1 cars shared headlights with the Boxster, a detail that divided opinion among purists at the time. Clean examples are now appreciated as accessible modern classics with strong GT and Turbo variants.',
  '996.2': 'The 996.2 refresh brought distinct new headlights and refinements to the water-cooled flat-six, addressing the most visible criticism of the original. GT3 and Turbo models from this generation have appreciated significantly, while base Carrera models remain among the most affordable 911s on the market. The 996.2 is increasingly viewed as an undervalued entry point into the modern 911 lineage.',
  '997.1': 'Arriving in 2004, the 997.1 restored the round headlight design and drew heavily on classic 911 styling cues, winning back many who had rejected the 996. The water-cooled mechanicals were carried over and refined, with significant improvements to chassis dynamics. GT3 and Turbo variants from this generation command consistent premiums at auction.',
  '997.2': 'The 997.2 introduced direct fuel injection across the lineup and added the limited-edition Sport Classic and Speedster, both of which now carry substantial collector premiums. Its GT3 RS 4.0 is widely considered one of the greatest driver\'s Porsches ever built. The 997.2 generation represents the last naturally aspirated Carrera before turbocharging became standard.',
  '991.1': 'The 991.1 brought a wider, longer body and a new seven-speed manual gearbox, along with the final naturally aspirated flat-six offered in a base Carrera. Its chassis refinement and electric power steering drew mixed reactions initially, but the GT3, GT3 RS, and R have since become celebrated as modern benchmarks. Values for GT variants have risen firmly as the air-cooled era recedes further.',
  '991.2': 'The 991.2 introduced a twin-turbocharged 3.0-liter flat-six to the base Carrera lineup, replacing the naturally aspirated engine and marking a significant shift in character. The GT3 and GT2 RS retained high-revving naturally aspirated and forced-induction identities respectively, earning widespread critical acclaim. The limited-production 991.2 Speedster has already emerged as one of the most sought-after modern Porsches.',
  '992':   'The 992 is the most refined and technologically advanced 911 to date, featuring a wider body, an 8-speed PDK, and turbocharged engines across the Carrera range as standard. Aerodynamics, chassis electronics, and interior quality represent substantial leaps over the outgoing 991. The 992 GT3 and GT3 RS have drawn particular praise for delivering uncompromised track performance in a road-legal package.',
  '992.1': 'The 992.1 launched as the widest and most powerful base Carrera in 911 history, with a 3.0-liter twin-turbocharged flat-six producing 379 horsepower and an eight-speed PDK as standard. Limited-production variants including the S/T, Sport Classic, and Dakar broadened the generation\'s collector appeal well beyond the GT cars. GT3 and GT3 RS values have strengthened quickly, with the naturally aspirated GT cars commanding premiums as turbocharging became ubiquitous across the Carrera range.',
  '992.2': 'The 992.2 facelift arrived for the 2025 model year with revised styling, updated powertrain calibrations, and expanded driver assistance and connectivity across the lineup. It continues the twin-turbocharged Carrera formula established by the 992.1 while refining the interior and aerodynamics throughout. As a generation still in active production, long-term collector values have yet to be established.',
}

export default function VariantIndex() {
  const { modelSlug, seg1, seg2 } = useParams()
  const model     = ALL_MODELS.find(m => m.slug === modelSlug)
  const modelLine = MODEL_LINE[modelSlug]
  const groups    = GENERATION_GROUPS[modelSlug] ?? {}

  // seg1 is a group key (997) → seg2 is the actual generation (997.1)
  // seg1 is a flat gen (964)  → seg1 itself is the generation
  const isGrouped  = Object.hasOwn(groups, seg1)
  const groupSlug  = isGrouped ? seg1 : null
  const generation = isGrouped ? seg2 : seg1

  const variants = VARIANTS[modelSlug]?.[generation] ?? []

  const [groupStats, setGroupStats] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    let stale = false // ignore responses that land after a navigation
    setLoading(true)
    setError(null)
    // Cross-listed lots are re-tagged with the host variant so they roll into
    // that card's count, average, and sparkline. These stay row-level fetches:
    // they're selected by id or title pattern, which SQL grouping can't express.
    // The filters are narrow, so the row count is tiny.
    const crossByVariant = CROSS_LISTINGS[modelSlug]?.[generation] ?? {}
    const extras = Object.entries(crossByVariant).flatMap(([hostVariant, entries]) =>
      entries.map(e =>
        fetchAuctionResults(e.params).then(rows =>
          groupStatsFromRows(
            hostVariant,
            rows.filter(r =>
              e.ids?.includes(r.id) ||
              (e.titlePattern != null && new RegExp(e.titlePattern, 'i').test(r.lot_title ?? ''))
            )
          )
        )
      )
    )
    Promise.all([
      fetchAggregateStats({
        model_line: modelLine, generation, group_by: 'variant', monthly: true,
      }),
      ...extras,
    ])
      .then(([base, ...crossGroups]) => {
        if (stale) return
        // Fold each cross-listed group into its host variant's aggregate.
        const merged = indexByKey(base)
        for (const g of crossGroups) {
          merged[g.key] = mergeGroups(merged[g.key], g) ?? g
        }
        setGroupStats(Object.values(merged))
      })
      .catch(e => { if (!stale) setError(e.message) })
      .finally(() => { if (!stale) setLoading(false) })
    return () => { stale = true }
  }, [modelLine, modelSlug, generation])

  const byVariant = useMemo(() => indexByKey(groupStats), [groupStats])
  const genStats  = useMemo(() => combineStats(groupStats), [groupStats])

  const sortedVariants = useMemo(() => (
    [...variants].sort((a, b) =>
      statsFromGroup(byVariant[b]).avg - statsFromGroup(byVariant[a]).avg)
  ), [variants, byVariant])

  if (!model) return <Navigate to="/" replace />

  if (variants.length === 1) {
    const base = groupSlug ? `/${modelSlug}/${groupSlug}/${generation}` : `/${modelSlug}/${generation}`
    return <Navigate to={`${base}/${toSlug(variants[0])}`} replace />
  }

  const crumbs = [
    { label: 'Markets',   to: '/' },
    { label: model.label, to: `/${modelSlug}` },
  ]
  if (groupSlug) crumbs.push({ label: groupSlug, to: `/${modelSlug}/${groupSlug}` })
  crumbs.push({ label: generation })

  const variantBase = groupSlug
    ? `/${modelSlug}/${groupSlug}/${generation}`
    : `/${modelSlug}/${generation}`

  return (
    <div className="inner">
      <div className="page-header">
        <Breadcrumb crumbs={crumbs} />
      </div>

      <div className="gen-hero">
        <div className="gen-hero-left">
          <div>
            <div className="gen-hero-eyebrow">Porsche {model.label}</div>
            <h1 className="gen-hero-title">{generation}</h1>
          </div>
          {GEN_DESCRIPTIONS[generation] && (
            <p className="gen-hero-desc">{GEN_DESCRIPTIONS[generation]}</p>
          )}
          <div className="gen-hero-stats">
            {GEN_YEARS[generation] && (
              <div className="gen-hero-stat">
                <span className="gen-hero-stat-label">Years</span>
                <span className="gen-hero-stat-value">{GEN_YEARS[generation]}</span>
              </div>
            )}
            <div className="gen-hero-stat">
              <span className="gen-hero-stat-label">Avg Sale</span>
              <span className="gen-hero-stat-value">{fmtVal(genStats.avg)}</span>
            </div>

          </div>
        </div>

        <div className="gen-hero-right">
          {GEN_IMAGES[generation] && (
            <img
              src={GEN_IMAGES[generation]}
              alt={`${model.label} ${generation}`}
              className="gen-hero-img"
            />
          )}
        </div>
      </div>

      {loading && <p className="status">Loading…</p>}
      {error   && <p className="status error">Error: {error}</p>}

      {!loading && !error && (
        <div className="card-grid">
          {sortedVariants.map(variant => {
            const group   = byVariant[variant]
            const stats   = statsFromGroup(group)
            const monthly = toMonthlySeries(group?.monthly)
            return (
              <Link
                key={variant}
                to={`${variantBase}/${toSlug(variant)}`}
                className="index-card"
              >
                <div className="index-card-header">
                  <span className="index-card-name">{variantLabel(model, variant)}</span>
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
  )
}
