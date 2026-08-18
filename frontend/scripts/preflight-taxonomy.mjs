#!/usr/bin/env node
/**
 * Preflight: find auction data the site cannot display.
 *
 * The frontend renders from curated whitelists in src/data/taxonomy.js — a card
 * exists only if its generation/variant is listed there. Ingest, meanwhile, writes
 * whatever it classifies. When a run produces a generation or variant the taxonomy
 * doesn't know, those rows land in the database and are silently invisible: no card,
 * no counts, and they're excluded from the parent's totals too.
 *
 * Run this after every ingest. Anything reported is either a taxonomy entry to add
 * or a classifier bug to fix.
 *
 *   node scripts/preflight-taxonomy.mjs [--api http://localhost:8000/api/v1] [--json]
 *
 * Exit code 1 if orphaned rows exist, so it can gate a pipeline.
 */
import {
  MODEL_LINE, ALL_MODELS, VARIANT_MODELS, GENERATION_GROUPS, GENERATIONS, VARIANTS,
} from '../src/data/taxonomy.js'

const args = process.argv.slice(2)
const API = args.includes('--api') ? args[args.indexOf('--api') + 1]
                                   : 'http://localhost:8000/api/v1'
const AS_JSON = args.includes('--json')

async function agg(params) {
  const url = `${API}/stats/aggregate?${new URLSearchParams(params)}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${url}`)
  return res.json()
}

// The generation values a slug can actually render: group entries expand to their
// children, flat entries stand for themselves. Mirrors GenerationIndex.
function renderableGenerations(slug) {
  const groups = GENERATION_GROUPS[slug] ?? {}
  return new Set((GENERATIONS[slug] ?? []).flatMap(g => groups[g] ?? [g]))
}

const findings = []
const record = (f) => findings.push(f)

for (const model of ALL_MODELS) {
  const { slug, type } = model
  const modelLine = MODEL_LINE[slug]
  if (!modelLine) continue // 'group' models (transaxle) have no rows of their own

  if (type === 'variant-model') {
    // No generation level — cards come straight from VARIANT_MODELS.
    const known = new Set(VARIANT_MODELS[slug] ?? [])
    for (const g of await agg({ group_by: 'variant', model_line: modelLine })) {
      if (!known.has(g.key)) {
        record({ slug, modelLine, level: 'variant', generation: null,
                 value: g.key, rows: g.count })
      }
    }
    continue
  }

  if (type === 'series') {
    const known = renderableGenerations(slug)
    for (const g of await agg({ group_by: 'generation', model_line: modelLine })) {
      if (!known.has(g.key)) {
        record({ slug, modelLine, level: 'generation', generation: null,
                 value: g.key, rows: g.count })
      }
    }
    // Variants are only reachable through a generation the site can render.
    for (const generation of known) {
      const knownVariants = new Set(VARIANTS[slug]?.[generation] ?? [])
      if (!knownVariants.size) continue // no curated list => page shows nothing to check
      for (const g of await agg({ group_by: 'variant', model_line: modelLine, generation })) {
        if (!knownVariants.has(g.key)) {
          record({ slug, modelLine, level: 'variant', generation,
                   value: g.key, rows: g.count })
        }
      }
    }
  }
  // 'standalone' models route straight to MarketDetail, which filters only on
  // model_line — nothing can be orphaned by a taxonomy whitelist there.
}

const totalRows = findings.reduce((n, f) => n + f.rows, 0)

if (AS_JSON) {
  console.log(JSON.stringify({ orphanedRows: totalRows, findings }, null, 2))
} else if (!findings.length) {
  console.log('✓ No orphaned data — every generation and variant in the database has a home in the UI.')
} else {
  console.log(`✗ ${totalRows} row(s) in the database cannot be displayed by the site.\n`)
  const gens = findings.filter(f => f.level === 'generation')
  const vars = findings.filter(f => f.level === 'variant')

  if (gens.length) {
    console.log('  Unrenderable generations (not in GENERATIONS / GENERATION_GROUPS):')
    for (const f of gens.sort((a, b) => b.rows - a.rows)) {
      console.log(`    ${f.slug.padEnd(11)} generation "${f.value}"  — ${f.rows} rows`)
    }
    console.log()
  }
  if (vars.length) {
    console.log('  Unrenderable variants (not in VARIANTS / VARIANT_MODELS):')
    for (const f of vars.sort((a, b) => b.rows - a.rows)) {
      const where = f.generation ? `${f.slug} / ${f.generation}` : f.slug
      console.log(`    ${where.padEnd(20)} variant "${f.value}"  — ${f.rows} rows`)
    }
    console.log()
  }
  console.log('  Each is either a taxonomy entry to add, or a classifier bug to fix.')
}

process.exit(findings.length ? 1 : 0)
