// slug → DB model_line value
export const MODEL_LINE = {
  // Road cars
  '911':        '911',
  '356':        '356',
  'cayman':     'Cayman',
  'boxster':    'Boxster',
  // Transaxle & 914
  '914':        '914',
  '924':        '924',
  '944':        '944',
  '968':        '968',
  '928':        '928',
  // Specialty
  '959':        '959',
  'carrera-gt': 'Carrera GT',
  '918-spyder': '918 Spyder',
  // Race cars
  '911-race':   '911 Race',
  '911-gt1':    '911 GT1',
  '917':        '917',
  '956':        '956',
  '962':        '962',
  '935':        '935',
  '934':        '934',
  '908':        '908',
  '907':        '907',
  '906':        '906',
  '904':        '904',
  '550':        '550',
  'rs60':       'RS60',
  '718-rsk':    '718 RSK',
  'rs-spyder':  'RS Spyder',
}

// category drives which section on MarketHome; type drives routing
export const ALL_MODELS = [
  // ── Model Lines ──────────────────────────────────────────────────────────────
  { slug: '911',        label: '911',        type: 'series',        category: 'series' },
  { slug: 'cayman',     label: 'Cayman',     type: 'series',        category: 'series' },
  { slug: 'boxster',    label: 'Boxster',    type: 'series',        category: 'series' },
  { slug: '356',        label: '356',        type: 'series',        category: 'series' },
  { slug: '914',        label: '914',        type: 'variant-model', category: 'series' },
  { slug: 'transaxle',  label: 'Transaxle',  type: 'group',         category: 'series' },
  // ── Transaxle children (routable, not shown as their own home section) ────────
  { slug: '924',        label: '924',        type: 'variant-model', category: 'transaxle' },
  { slug: '944',        label: '944',        type: 'variant-model', category: 'transaxle' },
  { slug: '968',        label: '968',        type: 'standalone',    category: 'transaxle' },
  { slug: '928',        label: '928',        type: 'standalone',    category: 'transaxle' },
  // ── Specialty Models ──────────────────────────────────────────────────────────
  { slug: '959',        label: '959',        type: 'standalone', category: 'specialty' },
  { slug: 'carrera-gt', label: 'Carrera GT', type: 'standalone', category: 'specialty' },
  { slug: '918-spyder', label: '918 Spyder', type: 'standalone', category: 'specialty' },
  // ── Race Cars ─────────────────────────────────────────────────────────────────
  { slug: '911-race',   label: '911',        type: 'series',     category: 'race' },
  { slug: '911-gt1',   label: '911 GT1',    type: 'standalone', category: 'race' },
  { slug: '917',        label: '917',        type: 'standalone', category: 'race' },
  { slug: '956',        label: '956',        type: 'standalone', category: 'race' },
  { slug: '962',        label: '962',        type: 'standalone', category: 'race' },
  { slug: '935',        label: '935',        type: 'standalone', category: 'race' },
  { slug: '934',        label: '934',        type: 'standalone', category: 'race' },
  { slug: '908',        label: '908',        type: 'standalone', category: 'race' },
  { slug: '907',        label: '907',        type: 'standalone', category: 'race' },
  { slug: '906',        label: '906',        type: 'standalone', category: 'race' },
  { slug: '904',        label: '904',        type: 'standalone', category: 'race' },
  { slug: '550',        label: '550 Spyder', type: 'standalone', category: 'race' },
  { slug: 'rs60',       label: 'RS60',       type: 'standalone', category: 'race' },
  { slug: '718-rsk',    label: '718 RSK',    type: 'standalone', category: 'race' },
  { slug: 'rs-spyder',  label: 'RS Spyder',  type: 'standalone', category: 'race' },
]

// Child model slugs for "group" models (a card that opens into several models,
// the way the 911 opens into generations).
export const GROUP_CHILDREN = {
  'transaxle': ['924', '944', '968', '928'],
}

// Curated variant lists for "variant-model" models — models that split into
// trims (like 924 Carrera GT / 944 Turbo) but have no generation level.
// Values match the DB `variant` field so results filter cleanly.
export const VARIANT_MODELS = {
  '924': ['Carrera GT', 'Turbo', 'base'],
  '944': ['Turbo', 'S2', 'S', 'base'],
  '914': ['914/6', 'base'],
}

// Card image + production years for the transaxle children and 914, used by
// GroupIndex / VariantModelIndex / MarketDetail.
export const TRANSAXLE_META = {
  '924': { years: '1976–1988', img: null },
  '944': { years: '1982–1991', img: '/images/Front_page_cards/Regular_models/944.png' },
  '968': { years: '1992–1995', img: null },
  '928': { years: '1978–1995', img: null },
  '914': { years: '1969–1976', img: '/images/Front_page_cards/Regular_models/porsche%20914.jpg' },
}

// Groups that have sub-generations; keyed by the group URL slug
export const GENERATION_GROUPS = {
  '911': {
    '996': ['996.1', '996.2'],
    '997': ['997.1', '997.2'],
    '991': ['991.1', '991.2'],
    '992': ['992.1', '992.2'],
  },
  'cayman': {
    '987': ['987.1', '987.2'],
  },
  'boxster': {
    '987': ['987.1', '987.2'],
  },
}

// Top-level generation list shown on GenerationIndex (groups collapsed to one entry)
export const GENERATIONS = {
  '911':      ['F-Body', 'G-Body', '964', '993', '996', '997', '991', '992'],
  '356':      ['Pre-A', '356 A', '356 B', '356 C'],
  'cayman':   ['987', '981', '718'],
  'boxster':  ['986', '987', '981', '718'],
  '911-race': ['F-Body', 'G-Body', '964', '993', '996', '997', '991', '992'],
}

export const VARIANTS = {
  '911': {
    'F-Body': [
      '911', '911S', '911T', '911E', '911L', '911R',
      'Carrera RS 2.7', 'S/T',
    ],
    'G-Body': [
      'Speedster', 'Turbo 3.3 Slant Nose', '930 Turbo',
      'Carrera 2.7 MFI', 'Carrera 2.7', 'Carrera 3.2', 'SC', '911S', '911',
    ],
    '964': [
      'Carrera', 'Carrera RS', 'RS 3.8', 'RS America',
      'Turbo', 'Turbo S', 'Speedster',
    ],
    '993': [
      'Carrera', 'Carrera S', 'Carrera RS',
      'Turbo', 'Turbo S', 'GT2',
    ],
    '996.1': ['Carrera', 'Carrera S', 'Turbo', 'GT3'],
    '996.2': ['Carrera', 'Carrera S', 'Turbo', 'Turbo S', 'GT3', 'GT3 RS', 'GT2'],
    '997.1': [
      'Carrera', 'Carrera S',
      'Turbo', 'GT3', 'GT3 RS', 'GT2',
    ],
    '997.2': [
      'Carrera', 'Carrera S', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'GT3 RS 4.0', 'GT2 RS', 'Sport Classic', 'Speedster',
    ],
    '991.1': [
      'Carrera', 'Carrera S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'R',
    ],
    '991.2': [
      'Carrera', 'Carrera S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'GT2 RS', 'Speedster',
    ],
    '992.1': [
      'Carrera', 'Carrera S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'S/T', 'Sport Classic', 'Dakar',
    ],
    '992.2': [
      'Carrera', 'Carrera S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS',
    ],
  },
  '356': {
    'Pre-A':  ['Coupe', 'Cabriolet', 'Speedster'],
    '356 A':  ['Coupe', 'Cabriolet', 'Speedster'],
    '356 B':  ['Coupe', 'Roadster', 'Cabriolet', 'Notchback'],
    '356 C':  ['Coupe', 'Cabriolet'],
  },
  'cayman': {
    '987.1': ['base', 'S'],
    '987.2': ['base', 'S', 'R'],
    '981': ['base', 'S', 'GTS', 'GT4'],
    '718': ['base', 'S', 'GTS', 'GT4', 'GT4 RS'],
  },
  'boxster': {
    '986': ['base', 'S'],
    '987.1': ['base', 'S'],
    '987.2': ['base', 'S', 'Spyder', 'GTS'],
    '981': ['base', 'S', 'GTS', 'Spyder'],
    '718': ['base', 'S', 'GTS', 'Spyder', 'Spyder RS'],
  },
  '911-race': {
    'F-Body':  ['RSR'],
    'G-Body':  ['RSR', 'RSR Turbo'],
    '964':     ['RSR 3.8', 'Carrera Cup'],
    '993':     ['GT2 R', 'Cup 3.8 RSR', 'Carrera Cup'],
    '996':     ['GT3 Cup', 'GT3 RSR', 'Carrera Cup'],
    '997':     ['GT3 RSR', 'GT3 Cup'],
    '991':     ['RSR', 'GT2 RS Clubsport', 'GT3 Cup'],
    '992':     ['GT3 Cup'],
  },
}

// Hero image filename (served from /images/variants/) for each variant.
const _h = (variants, img) => Object.fromEntries(variants.map(v => [v, img]))

export const VARIANT_HERO = {
  '911': {
    'F-Body':  _h(VARIANTS['911']['F-Body'],  null),
    'G-Body':  _h(VARIANTS['911']['G-Body'],  null),
    '964':     _h(VARIANTS['911']['964'],     null),
    '993': {
      ..._h(VARIANTS['911']['993'],  null),
      'Carrera RS': '911_993_rs.jpg',
      'Turbo':      '911_993_turbo.jpg',
      'Turbo S':    '911_993_turbo.jpg',
    },
    '996.1':   _h(VARIANTS['911']['996.1'],  null),
    '996.2':   _h(VARIANTS['911']['996.2'],  null),
    '997.1': {
      ..._h(VARIANTS['911']['997.1'], null),
      'GT3':    '911_997-1_gt3.jpg',
      'GT3 RS': '911_997-1_gt3rs.jpg',
      'GT2':    '911_997-2_gt2.jpg',
    },
    '997.2': {
      ..._h(VARIANTS['911']['997.2'], null),
      'GT3 RS': '911_997-2_gt3rs.jpg',
      'GT2 RS': '911_997-2_gt2rs.jpg',
    },
    '991.1':   _h(VARIANTS['911']['991.1'],  null),
    '991.2':   _h(VARIANTS['911']['991.2'],  null),
    '992.1':   _h(VARIANTS['911']['992.1'],  null),
    '992.2':   _h(VARIANTS['911']['992.2'],  null),
  },
  '356':     {},
  'cayman':  {
    '718': {
      ..._h(VARIANTS['cayman']['718'], null),
      'GT4':    'cayman_718_gt4.jpeg',
      'GT4 RS': 'cayman_718_gt4.jpeg',
    },
  },
  'boxster':  {
    '718': {
      ..._h(VARIANTS['boxster']['718'], null),
      'Spyder RS': 'boxster_718_spyder_rs.webp',
    },
  },
  '911-race': {},
}

// Lots cross-listed onto a second market page.  Keyed
// [modelSlug][generation][variant] → extra queries; lots whose title matches
// titlePattern (or whose id is in ids, for lots titled without the marker)
// appear on that page in addition to their home market.
// Example: the street-legal RSR 3.8 Strassenversions live in the race section
// but are also shown with the street RS 3.8s as standouts of the 964 line.
export const CROSS_LISTINGS = {
  '911': {
    '964': {
      'RS 3.8': [{
        params: { model_line: '911 Race', generation: '964', variant: 'RSR 3.8' },
        titlePattern: 'Strassenversion',
        // Strassenversion chassis WP0ZZZ96ZPS496107 at RM Villa Erba 2017,
        // titled plain 'Carrera RSR 3.8'
        ids: [27995],
      }],
    },
  },
}

// Hero image for standalone models
export const MODEL_HERO = {
  '959':        null,
  'carrera-gt': null,
  '918-spyder': null,
  '911-gt1':    null,
  '917':        null,
  '956':        null,
  '962':        null,
  '935':        null,
  '934':        null,
  '908':        null,
  '907':        null,
  '906':        null,
  '904':        null,
  '550':        null,
  'rs60':       null,
  '718-rsk':    null,
  'rs-spyder':  null,
}

// Card images for generation index and hero pages.
// Used by GenerationIndex, SubGenerationIndex, and VariantIndex.
export const GEN_IMAGES = {
  'F-Body': '/images/911_gen_page_cards/911R(1967)Fbodygenpic.jpeg',
  'G-Body': '/images/911_gen_page_cards/930turbogbodygen.jpg',
  '964':    '/images/911_gen_page_cards/porsche964RS.png',
  '993':    '/images/911_gen_page_cards/993GT2.png',
  '996':    '/images/911_gen_page_cards/996.jpeg',
  '996.1':  '/images/911_gen_page_cards/996.jpeg',
  '996.2':  '/images/911_gen_page_cards/996.jpeg',
  '997':    '/images/911_gen_page_cards/997GT2.png',
  '997.1':  '/images/911_gen_page_cards/997GT2.png',
  '997.2':  '/images/911_gen_page_cards/997GT2.png',
  '991':    '/images/911_gen_page_cards/991gt2rs.png',
  '991.1':  '/images/911_gen_page_cards/991gt2rs.png',
  '991.2':  '/images/911_gen_page_cards/991gt2rs.png',
  '992':    '/images/911_gen_page_cards/911st.png',
  '992.1':  '/images/911_gen_page_cards/911st.png',
  '992.2':  '/images/911_gen_page_cards/911st.png',
}

// Production year spans for all generations and sub-generations.
// Used by GenerationIndex, SubGenerationIndex, and VariantIndex.
export const GEN_YEARS = {
  'F-Body': '1963–1973',
  'G-Body': '1974–1989',
  '964':    '1989–1994',
  '993':    '1994–1998',
  '996':    '1997–2005',
  '996.1':  '1997–2001',
  '996.2':  '2001–2005',
  '997':    '2004–2012',
  '997.1':  '2004–2008',
  '997.2':  '2008–2012',
  '991':    '2011–2019',
  '991.1':  '2011–2016',
  '991.2':  '2016–2019',
  '992':    '2019–present',
  '992.1':  '2019–2024',
  '992.2':  '2025–present',
  '986':    '1996–2004',
  '987':    '2004–2012',
  '987.1':  '2004–2008',
  '987.2':  '2008–2012',
  '981':    '2012–2016',
  '718':    '2016–present',
}

