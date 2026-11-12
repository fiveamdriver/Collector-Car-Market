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
  // Restomods — coachbuilders get their own model line so their seven-figure
  // sales don't sit inside the donor generation's street average.
  'singer':        'Singer',
  'gunther-werks': 'Gunther Werks',
  'emory':         'Emory',
  'ruf':           'RUF',
  // Race cars
  '911-race':   '911 Race',
  '911-gt1':    '911 GT1',
  'cayman-gt4-clubsport': 'Cayman Race',
  // Transaxle race cars: one group card on the home page, a page per model.
  '924-race':   '924 Race',
  '944-race':   '944 Race',
  '968-race':   '968 Race',
  '928-race':   '928 Race',
  '917':        '917',
  '910':        '910',
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
  { slug: '968',        label: '968',        type: 'variant-model', category: 'transaxle' },
  { slug: '928',        label: '928',        type: 'variant-model', category: 'transaxle' },
  // ── Specialty Models ──────────────────────────────────────────────────────────
  { slug: '959',        label: '959',        type: 'standalone', category: 'specialty' },
  { slug: 'carrera-gt', label: 'Carrera GT', type: 'standalone', category: 'specialty' },
  { slug: '918-spyder', label: '918 Spyder', type: 'standalone', category: 'specialty' },
  // ── Restomods ─────────────────────────────────────────────────────────────────
  { slug: 'singer',        label: 'Singer',        type: 'standalone', category: 'restomod' },
  { slug: 'gunther-werks', label: 'Gunther Werks', type: 'standalone', category: 'restomod' },
  { slug: 'emory',         label: 'Emory Motorsports', type: 'standalone', category: 'restomod' },
  // ── Tuners ────────────────────────────────────────────────────────────────────
  { slug: 'ruf',           label: 'RUF',           type: 'standalone', category: 'ruf' },
  // ── Race Cars ─────────────────────────────────────────────────────────────────
  { slug: '911-race',   label: '911',        type: 'series',     category: 'race' },
  { slug: '911-gt1',   label: '911 GT1',    type: 'standalone', category: 'race' },
  { slug: '917',        label: '917',        type: 'standalone', category: 'race' },
  { slug: '935',        label: '935',        type: 'series',     category: 'race' },
  { slug: '962',        label: '962',        type: 'standalone', category: 'race' },
  { slug: '550',        label: '550 Spyder', type: 'standalone', category: 'race' },
  { slug: '718-rsk',    label: '718 RSK',    type: 'standalone', category: 'race' },
  { slug: 'rs60',       label: 'RS60',       type: 'standalone', category: 'race' },
  { slug: '904',        label: '904',        type: 'standalone', category: 'race' },
  { slug: '906',        label: '906',        type: 'standalone', category: 'race' },
  { slug: '910',        label: '910',        type: 'standalone', category: 'race' },
  { slug: '907',        label: '907',        type: 'standalone', category: 'race' },
  { slug: '908',        label: '908',        type: 'standalone', category: 'race' },
  { slug: '934',        label: '934',        type: 'standalone', category: 'race' },
  { slug: '956',        label: '956',        type: 'standalone', category: 'race' },
  { slug: 'rs-spyder',  label: 'RS Spyder',  type: 'standalone', category: 'race' },
  { slug: 'cayman-gt4-clubsport', label: 'Cayman GT4 Clubsport', type: 'standalone', category: 'race' },
  { slug: 'transaxle-race', label: 'Transaxle Race Cars', type: 'group', category: 'race' },
  // Children of 'transaxle-race': reached through its group page, not shown on the home page.
  { slug: '924-race', label: '924', type: 'variant-model', category: 'transaxle-race' },
  { slug: '944-race', label: '944', type: 'variant-model', category: 'transaxle-race' },
  { slug: '968-race', label: '968', type: 'variant-model', category: 'transaxle-race' },
  { slug: '928-race', label: '928', type: 'variant-model', category: 'transaxle-race' },
]

// Child model slugs for "group" models (a card that opens into several models,
// the way the 911 opens into generations).
export const GROUP_CHILDREN = {
  'transaxle': ['924', '944', '968', '928'],
  'transaxle-race': ['924-race', '944-race', '968-race', '928-race'],
}

// Curated variant lists for "variant-model" models — models that split into
// trims (like 924 Carrera GT / 944 Turbo) but have no generation level.
// Values match the DB `variant` field so results filter cleanly.
// The entry-level card is keyed 'base' and rendered with the model name, so
// the S-suffix cars (924S / 944S / 928S) live there rather than in a card of
// their own.  Competition cars sit on separate "<line> Race" model lines and
// are deliberately absent here.
export const VARIANT_MODELS = {
  '924': ['Carrera GTS', 'Carrera GT', 'Turbo', 'base'],
  '944': ['Turbo S', 'Turbo', 'S2', 'base'],
  '968': ['Turbo S', 'Club Sport', 'base'],
  '928': ['GTS', 'GT', 'S4', 'Club Sport', 'base'],
  '914': ['914/6', 'base'],
  // Race-car trims as the ingests file them ('Race' = an unnamed race build).
  '924-race': ['GTP', 'Carrera GTR', 'GTR', 'D Production', 'Race'],
  '944-race': ['GTP', 'Turbo Cup', 'Race'],
  '968-race': ['Turbo RS', 'Race'],
  '928-race': ['Race'],
}

// Card image + production years for the transaxle children and 914, used by
// GroupIndex / VariantModelIndex / MarketDetail.
export const TRANSAXLE_META = {
  '924': { years: '1976–1988', img: null },
  '944': { years: '1982–1991', img: '/images/Front_page_cards/Regular_models/944.png' },
  '968': { years: '1992–1995', img: null },
  '928': { years: '1978–1995', img: null },
  '914': { years: '1969–1976', img: '/images/Front_page_cards/Regular_models/porsche%20914.jpg' },
  '924-race': { years: '1978–1982', img: '/images/Racecar/924_carreraGTR.jpeg' },
  '944-race': { years: '1981–1991', img: null },
  '968-race': { years: '1992–1994', img: null },
  '928-race': { years: '1978–1987', img: null },
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
  '935':      ['Classic', 'Modern'],
}

export const VARIANTS = {
  '911': {
    'F-Body': [
      // 'S/T' left out until a sale comes in — its photo stays in VARIANT_HERO.
      '911', '911S', '911T', '911E', '911L', '911R',
      'Carrera RS 2.7', 'Targa',
    ],
    'G-Body': [
      'Speedster', 'Turbo 3.3 Slant Nose', '930 Turbo',
      'Carrera 2.7 MFI', 'Carrera RS 3.0', 'Carrera 2.7', 'Carrera 3.0', 'Carrera 3.2 Club Sport', 'Carrera 3.2',
      'SC RS', 'SC', '911S', '911',
      'Targa', 'Cabriolet',
    ],
    // Carrera 4 starts here — the 964 was the first all-wheel-drive 911.
    '964': [
      // The 964 was sold as the rear-drive Carrera 2 and the all-wheel-drive
      // Carrera 4, so those are its cards; there is no generic 'Carrera'.
      // The Turbo is split by engine: 3.3 (MY1991-92) and 3.6 (MY1993-94).
      'Carrera 2', 'Carrera 4', 'Carrera RS', 'RS 3.8', 'Carrera 4 Leichtbau', 'RS America',
      'Turbo 3.3', 'Turbo 3.6', 'Turbo S', 'Speedster', 'Targa', 'Cabriolet',
    ],
    // Carrera 4S starts here, alongside the first glass-roof Targa.
    '993': [
      'Carrera', 'Carrera 4', 'Carrera S', 'Carrera 4S', 'Carrera RS',
      'Turbo', 'Turbo S', 'GT2', 'Targa', 'Cabriolet',
    ],
    // No 996.1 Targa or 4S: both arrived with the MY2002 facelift. The 996 Turbo
    // and GT2 have one card each, on 996.2 (Porsche lists the Turbo as a single
    // series, "911 Turbo Coupé (2001-05)").
    '996.1': ['Carrera', 'Carrera 4', 'GT3', 'Cabriolet'],
    '996.2': [
      // No Carrera 4 card (owner, 2026-11-08): the US got the 996.2 C4 only as a
      // Cabriolet, and its one coupe sale (a Gemballa GTR 500) is on Carrera.
      'Carrera', 'Carrera 4S',
      'Turbo', 'Turbo S', 'GT3', 'GT3 RS', 'GT2', 'Targa', 'Cabriolet',
    ],
    '997.1': [
      'Carrera', 'Carrera 4', 'Carrera S', 'Carrera 4S',
      'Turbo', 'GT3', 'GT3 RS', 'GT2', 'Targa', 'Cabriolet',
    ],
    '997.2': [
      'Carrera', 'Carrera 4', 'Carrera S', 'Carrera 4S', 'Carrera GTS',
      'Turbo', 'Turbo S',
      // No GT2: the 997 GT2 (MY2008-09) was 997.1 only; the 997.2 got the GT2 RS.
      'GT3', 'GT3 RS', 'GT3 RS 4.0', 'GT2 RS', 'Sport Classic', 'Speedster',
      'Targa', 'Cabriolet',
    ],
    '991.1': [
      'Carrera', 'Carrera 4', 'Carrera S', 'Carrera 4S', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'R', 'Targa', 'Cabriolet',
    ],
    '991.2': [
      'Carrera', 'Carrera 4', 'Carrera S', 'Carrera 4S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'GT2 RS', 'Speedster', 'Targa', 'Cabriolet',
    ],
    // No Carrera 4 card (owner, 2026-11-12): 992.1 Carrera 4 sales sit on the
    // Carrera card; a title that says 4S goes to Carrera 4S.
    '992.1': [
      'Carrera', 'Carrera S', 'Carrera 4S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'S/T', 'Sport Classic', 'Dakar', 'Targa', 'Cabriolet',
    ],
    '992.2': [
      'Carrera', 'Carrera 4', 'Carrera S', 'Carrera 4S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'Targa', 'Cabriolet',
    ],
  },
  '356': {
    'Pre-A':  ['Coupe', 'Cabriolet', 'Speedster', 'Roadster'],
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
    '987.1': ['base', 'S', 'RS 60 Spyder'],
    '987.2': ['base', 'S', 'Spyder'],
    '981': ['base', 'S', 'GTS', 'Spyder'],
    '718': ['base', 'S', 'GTS', 'Spyder', 'Spyder RS'],
  },
  // No plain 'Clubsport' race cards: factory Clubsport 911s are street-legal and
  // live on their street card (only non-street-legal cars are race cars).
  '911-race': {
    'F-Body':  ['RSR'],
    'G-Body':  ['RSR', 'RSR Turbo'],
    '964':     ['RSR 3.8', 'Carrera Cup'],
    '993':     ['GT2 R', 'Cup 3.8 RSR', 'Carrera Cup'],
    '996':     ['GT3 Cup', 'GT3 RSR', 'GT3 R', 'Carrera Cup'],
    '997':     ['GT3 RSR', 'GT3 Cup'],
    '991':     ['RSR', 'GT3 R', 'GT2 RS Clubsport', 'GT3 Cup'],
    '992':     ['GT3 Cup', 'GT3 R', 'GT2 RS Clubsport'],
  },
  // One variant per era, so each generation card opens straight to its results.
  '935': {
    'Classic': ['base'],
    'Modern':  ['base'],
  },
}

// Hero image for each variant, as a full path under /images. Variants not
// listed here have no photo yet and show the empty hero panel.

// Cards shown only while they have at least one sale, keyed [model][generation].
export const HIDE_WHEN_EMPTY = {
  '911': {},
}

export const VARIANT_HERO = {
  '911': {
    'F-Body': {
      '911': '/images/911_variants/F-Body/1965_911.png',
      '911S': '/images/911_variants/F-Body/1967_911S.png',
      '911T': '/images/911_variants/F-Body/911T_FBODY.jpg',
      '911E': '/images/911_variants/F-Body/911E.jpeg',
      '911L': '/images/911_variants/F-Body/1968_911L.jpeg',
      '911R': '/images/911_gen_page_cards/911R(1967)Fbodygenpic.jpeg',
      'Carrera RS 2.7': '/images/911_variants/F-Body/1973_RS2.7.png',
      'S/T': '/images/911_variants/F-Body/1970_ST.jpg',
      'Targa': '/images/911_variants/F-Body/1967_911sTARGA.png',
    },
    'G-Body': {
      'Speedster':              '/images/911_variants/G-Body/1989_Porsche_911_Speedster.jpg',
      'Turbo 3.3 Slant Nose':   '/images/911_variants/G-Body/1988_turbo_slantnose.jpeg',
      '930 Turbo':              '/images/911_variants/G-Body/930_turbo.webp',
      'Carrera 2.7 MFI':        '/images/911_variants/G-Body/2.7MFI.webp',
      'Carrera RS 3.0':         '/images/911_variants/G-Body/carrera_rs3.0.webp',
      'Carrera 2.7':            '/images/911_variants/G-Body/1974_carrera2.7(non-mfi).webp',
      'Carrera 3.0':            '/images/911_variants/G-Body/1997_carrera3.0.jpg',
      'Carrera 3.2 Club Sport': '/images/911_variants/G-Body/3.2_clubsport_web.jpg',
      'Carrera 3.2':            '/images/911_variants/G-Body/carrera3.2.webp',
      'SC RS':                  '/images/911_variants/G-Body/911_SC_RS.jpeg',
      'SC':                     '/images/911_variants/G-Body/911SC.avif',
      '911S':                   '/images/911_variants/G-Body/911S.jpg',
      '911':                    '/images/911_variants/G-Body/911_coupe_web.jpg',
      'Targa':                  '/images/911_variants/G-Body/G_body_targa.webp',
      'Cabriolet':              '/images/911_variants/G-Body/g_body%20cabriole.webp',
    },
    '964': {
      'Carrera 2':           '/images/911_variants/964/964_carrera2.jpg',
      'Carrera 4':           '/images/911_variants/964/964_C4.jpeg',
      'Carrera RS':          '/images/911_variants/964/964_carrerars.webp',
      'RS 3.8':              '/images/911_variants/964/964_RS3.8.jpg',
      'Carrera 4 Leichtbau': '/images/911_variants/964/964_carrera4_leichtbau.jpg',
      'RS America':          '/images/911_variants/964/964_rsamerica_card.jpeg',
      'Turbo 3.3':           '/images/911_variants/964/964_turbo3.3.jpg',
      'Turbo 3.6':           '/images/911_variants/964/964_turbo36.avif',
      'Turbo S':             '/images/911_variants/964/1993-porsche-911-turbo-s-lightweight-6a9615d43cd69.webp',
      'Speedster':           '/images/911_variants/964/964_speedster.webp',
      'Targa':               '/images/911_variants/964/964_targa.jpeg',
      'Cabriolet':           '/images/911_variants/964/964_cabriolet.jpg',
    },
    '993': {
      'Carrera':    '/images/911_variants/993/993_carrera.webp',
      'Carrera 4':  '/images/911_variants/993/993_carrera4.webp',
      'Carrera S':  '/images/911_variants/993/993_carreraS.jpeg',
      'Carrera 4S': '/images/911_variants/993/993_C4S.webp',
      'Carrera RS': '/images/911_variants/993/993_carreraRS.jpeg',
      'Turbo':      '/images/911_variants/993/993_turbo.jpg',
      'Turbo S':    '/images/911_variants/993/993_turbos.jpg',
      'GT2':        '/images/911_variants/993/993_GT2.jpg',
      'Targa':      '/images/911_variants/993/993_targa.jpeg',
      'Cabriolet':  '/images/911_variants/993/993_cabriolet.jpg',
    },
    '996.1': {
      'Carrera':   '/images/911_variants/996/996.1/996.1_carrera.webp',
      'Carrera 4': '/images/911_variants/996/996.1/996.1_carrera4.avif',
      'GT3':       '/images/911_variants/996/996.1/996.1_GT3.jpg',
      'Cabriolet': '/images/911_variants/996/996.1/996.1_cabriolet.webp',
    },
    '996.2': {
      'Carrera':    '/images/911_variants/996/996.2/996.2_carrera.jpeg',
      'Carrera 4S': '/images/911_variants/996/996.2/996_C4S.jpg',
      'Turbo':      '/images/911_variants/996/996.2/996_turbo.jpg',
      'Turbo S':    '/images/911_variants/996/996.2/996_turboS.jpg',
      'GT3':        '/images/911_variants/996/996.2/996.2_GT3.jpg',
      'GT3 RS':     '/images/911_variants/996/996.2/996_GT3RS.webp',
      'GT2':        '/images/911_variants/996/996.2/996_GT2.jpeg',
      'Targa':      '/images/911_variants/996/996.2/996_targa.png',
      'Cabriolet':  '/images/911_variants/996/996.2/996.2_cabriolet.jpeg',
    },
    '997.1': {
      'Carrera':    '/images/911_variants/997/997.1/997.1_carrera.png',
      'Carrera 4':  '/images/911_variants/997/997.1/997.1_carrera4.jpeg',
      'Carrera S':  '/images/911_variants/997/997.1/997.1_carreraS.avif',
      'Carrera 4S': '/images/911_variants/997/997.1/997.1_C4S.avif',
      'Turbo':      '/images/911_variants/997/997.1/997.1_turbo.webp',
      'GT3':        '/images/911_variants/997/997.1/997.1_GT3.avif',
      'GT3 RS':     '/images/911_variants/997/997.1/997.1_GT3RS.png',
      'GT2':        '/images/911_variants/997/997.1/997.1_GT2.webp',
      'Targa':      '/images/911_variants/997/997.1/997.1_targa.jpg',
      'Cabriolet':  '/images/911_variants/997/997.1/997.1_cabriolet.jpeg',
    },
    '997.2': {
      'Carrera':      '/images/911_variants/997/997.2/997.2_carrera.jpg',
      'Carrera 4':    '/images/911_variants/997/997.2/997.2_C4.jpg',
      'Carrera S':    '/images/911_variants/997/997.2/997.2_C2S.jpeg',
      'Carrera 4S':   '/images/911_variants/997/997.2/997.2_C4S.jpeg',
      'Carrera GTS':  '/images/911_variants/997/997.2/997.2_carreragts.avif',
      'Turbo':        '/images/911_variants/997/997.2/997.2_turbo.jpg',
      'Turbo S':      '/images/911_variants/997/997.2/997.2_TurboS.jpg',
      'GT3':          '/images/911_variants/997/997.2/997.2_GT3.webp',
      'GT3 RS':       '/images/911_variants/997/997.2/997.2_GT3RS.webp',
      'GT3 RS 4.0':   '/images/911_variants/997/997.2/997.2_gt3rs4.0.jpg',
      'GT2 RS':       '/images/911_variants/997/997.2/997.2_gt2rs.webp',
      'Sport Classic': '/images/911_variants/997/997.2/997.2_sportclassic.jpg',
      'Speedster':    '/images/911_variants/997/997.2/997.2_speedster.jpg',
      'Targa':        '/images/911_variants/997/997.2/997.2_targa.jpeg',
      'Cabriolet':    '/images/911_variants/997/997.2/997.2_cabriolet.jpeg',
    },
    '991.1': {
      'Carrera':     '/images/911_variants/991/991.1/991.1_carrera.jpg',
      'Carrera 4':   '/images/911_variants/991/991.1/991.1_C4.jpeg',
      'Carrera S':   '/images/911_variants/991/991.1/991.1_carreraS.jpeg',
      'Carrera 4S':  '/images/911_variants/991/991.1/991.1_C4S.jpg',
      'Carrera GTS': '/images/911_variants/991/991.1/991.1_carreraGTS.jpg',
      'Turbo':       '/images/911_variants/991/991.1/991.1_turbo.jpeg',
      'Turbo S':     '/images/911_variants/991/991.1/991.1_turboS.webp',
      'GT3':         '/images/911_variants/991/991.1/991.1_GT3.webp',
      'GT3 RS':      '/images/911_variants/991/991.1/991.1_GT3RS.jpeg',
      'R':           '/images/911_variants/991/991.1/991.1_911R.png',
      'Targa':       '/images/911_variants/991/991.1/991.1_targa.jpg',
      'Cabriolet':   '/images/911_variants/991/991.1/991.1_cabriolet.jpg',
    },
    '991.2': {
      'Carrera':     '/images/911_variants/991/991.2/991.2_carrera.webp',
      'Carrera 4':   '/images/911_variants/991/991.2/991.2_carrera4.jpeg',
      'Carrera S':   '/images/911_variants/991/991.2/991.2_carreraS.jpeg',
      'Carrera 4S':  '/images/911_variants/991/991.2/991.2_carrera4S.jpeg',
      'Carrera T':   '/images/911_variants/991/991.2/991.2_carreraT.jpg',
      'Carrera GTS': '/images/911_variants/991/991.2/991.2_carreraGTS.webp',
      'Turbo':       '/images/911_variants/991/991.2/991.2_turbo.webp',
      'Turbo S':     '/images/911_variants/991/991.2/991.2_turboS.avif',
      'GT3':         '/images/911_variants/991/991.2/991.2_GT3.webp',
      'GT3 RS':      '/images/911_variants/991/991.2/991.2_GT3RS.jpg',
      'GT2 RS':      '/images/911_variants/991/991.2/991.2_GT2RS.jpg',
      'Speedster':   '/images/911_variants/991/991.2/991.2_speedster.jpeg',
      'Targa':       '/images/911_variants/991/991.2/991.2_targa.jpg',
      'Cabriolet':   '/images/911_variants/991/991.2/991.2_cabriolet.jpg',
    },
    '992.1': {
      'Carrera':       '/images/911_variants/992/992.1/992_carrera.avif',
      'Carrera S':     '/images/911_variants/992/992.1/992_carreraS.jpg',
      'Carrera 4S':    '/images/911_variants/992/992.1/992_C4S.jpg',
      'Carrera T':     '/images/911_variants/992/992.1/992_carrerat_card.jpg',
      'Carrera GTS':   '/images/911_variants/992/992.1/992_carreraGTS.jpg',
      'Turbo':         '/images/911_variants/992/992.1/992_turbo.webp',
      'Turbo S':       '/images/911_variants/992/992.1/992_TURBOS.webp',
      'GT3':           '/images/911_variants/992/992.1/992_GT3.jpg',
      'GT3 RS':        '/images/911_variants/992/992.1/992_GT3RS.webp',
      'S/T':           '/images/911_variants/992/992.1/911_ST/911_st3.jpg',
      'Sport Classic': '/images/911_variants/992/992.1/992_sportclassic.jpg',
      'Dakar':         '/images/911_variants/992/992.1/992_dakar.jpg',
      'Targa':         '/images/911_variants/992/992.1/992_targa.webp',
      'Cabriolet':     '/images/911_variants/992/992.1/992_cabriolet.webp',
    },
  },
  '356':     {},
  'cayman':  {
    '987.1': { 'base': '/images/Mid Engine/Cayman/987 cayman.jpg' },
    '981':   { 'GT4': '/images/Mid Engine/Cayman/cayman_718_gt4.jpeg' },
    '718':   { 'GT4 RS': '/images/Front_page_cards/Regular_models/GT4RS.png' },
  },
  'boxster':  {
    '987.2': { 'Spyder': '/images/boxsterspyder.png' },
    '981':   { 'Spyder': '/images/Mid Engine/Boxster/981spyder.jpg' },
    '718':   { 'Spyder RS': '/images/Front_page_cards/Regular_models/spyderrsfront.png' },
  },
  // Variant-models have no generation level, so these are keyed [slug][variant].
  '924': { 'Carrera GT': '/images/Front_page_cards/Regular_models/924_CarreraGT.png' },
  '944': {
    'Turbo': '/images/Front Engine/944 turbo.jpg',
    'base':  '/images/Front Engine/944.jpg',
  },
  '914': {
    '914/6': '/images/914 photos/914:6GT.jpeg',
    'base':  '/images/914 photos/1970-914:4.jpg',
  },
  '911-race': {},
  '935': {
    'Classic': { 'base': '/images/Front_page_cards/Racecars/935.png' },
    'Modern':  { 'base': '/images/Racecar/modern_935_web.jpg' },
  },
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

// Front-page card photo per model slug. Standalone model pages reuse it as
// their hero when MODEL_HERO has no dedicated image.
export const MODEL_IMAGES = {
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
  'ruf':           '/images/Front_page_cards/RUFCTR_YELLOWBIRD.jpeg',
  '911-race':   '/images/Front_page_cards/Racecars/RSR.jpg',
  '911-gt1':    '/images/Front_page_cards/Racecars/gt1.png',
  'cayman-gt4-clubsport': '/images/Front_page_cards/Racecars/cayman_gt4rs_clubsport.jpg',
  'transaxle-race': '/images/Racecar/924_carreraGTR.jpeg',
  '917':        '/images/Front_page_cards/Racecars/917.png',
  '910':        '/images/Front_page_cards/Racecars/910_1.jpeg',
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

// Hero image for standalone models
export const MODEL_HERO = {
  '959':        null,
  'carrera-gt': null,
  '918-spyder': null,
  'singer':        '/images/Front_page_cards/Restomod/singer_dls.jpg',
  'gunther-werks': '/images/Front_page_cards/Restomod/gunther_werks_f26.jpg',
  'emory':         '/images/Front_page_cards/Restomod/emory_motorsports.jpg',
  '911-gt1':    null,
  'cayman-gt4-clubsport': null,
  '917':        null,
  '910':        null,
  '956':        null,
  '962':        null,
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

// Extra zoom for a card photo whose car sits small in the frame, keyed by the
// photo path so it follows the photo wherever it's used as a card.
export const CARD_PHOTO_ZOOM = {
  '/images/911_variants/997/997.2/997.2_gt2rs.webp': 1.15,
  '/images/911_variants/997/997.2/997.2_TurboS.jpg': 1.15,
}

// Sub-generation cards (/911/996 -> 996.1, 996.2) become photo cards when they
// have a photo here. GEN_IMAGES is the hero photo;
// these are kept separate so a group doesn't show the same photo twice.
export const SUBGEN_CARD_IMAGES = {
  '996.1': '/images/911_variants/996/996.1/996.1_GT3.jpg',
  '996.2': '/images/911_variants/996/996.2/996_GT3RS.webp',
  '997.1': '/images/911_variants/997/997.1/997.1_GT3RS.png',
  '997.2': '/images/911_variants/997/997.2/997.2_gt3rs4.0.jpg',
  '991.1': '/images/911_variants/991/991.1/991.1_911R.png',
  '991.2': '/images/911_variants/991/991.2/991.2_GT2RS.jpg',
}

// Card images for generation index and hero pages.
// Used by GenerationIndex, SubGenerationIndex, and VariantIndex.
export const GEN_IMAGES = {
  '356 A':  '/images/Canepa Images/356.jpeg',
  'F-Body': '/images/911_gen_page_cards/2.7CARRERA_RS.png',
  'G-Body': '/images/911_gen_page_cards/930turbogbodygen.jpg',
  '964':    '/images/911_gen_page_cards/porsche964CarreraRS.png',
  '993':    '/images/911_gen_page_cards/993GT2.png',
  '996':    '/images/911_gen_page_cards/996.2_carrera.jpeg',
  '996.1':  '/images/911_variants/996/996.1/996.1_GT3.jpg',
  '996.2':  '/images/911_variants/996/996.2/996_GT3RS.webp',
  '997':    '/images/911_gen_page_cards/997GT2.png',
  '997.1':  '/images/911_gen_page_cards/997GT2.png',
  '997.2':  '/images/911_gen_page_cards/997GT2.png',
  '991':    '/images/911_gen_page_cards/991gt2rs.png',
  '991.1':  '/images/911_gen_page_cards/991gt2rs.png',
  '991.2':  '/images/911_gen_page_cards/991gt2rs.png',
  '992':    '/images/911_gen_page_cards/992ST_card.jpg',
  '992.1':  '/images/911_variants/992/992.1/911_ST/911ST_992.jpg',
  '992.2':  '/images/911_variants/992/992.1/911_ST/911ST_992.jpg',
  'Classic': '/images/Front_page_cards/Racecars/935.png',
  'Modern':  '/images/Racecar/modern_935_web.jpg',
}

// Production year spans for all generations and sub-generations.
// Used by GenerationIndex, SubGenerationIndex, and VariantIndex.
export const GEN_YEARS = {
  '356 A':  '1955–1959',
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

// Display names for generations whose URL slug isn't what the page should show
export const GEN_LABELS = {
  'Classic': '1976–1979',
  'Modern':  '2019–2020',
}

