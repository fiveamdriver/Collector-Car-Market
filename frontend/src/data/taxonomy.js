// slug → DB model_line value
export const MODEL_LINE = {
  '911':        '911',
  'cayman':     'Cayman',
  'boxster':    'Boxster',
  '959':        '959',
  'carrera-gt': 'Carrera GT',
  '918-spyder': '918 Spyder',
}

export const ALL_MODELS = [
  { slug: '911',        label: '911',        type: 'series' },
  { slug: 'cayman',     label: 'Cayman',     type: 'series' },
  { slug: 'boxster',    label: 'Boxster',    type: 'series' },
  { slug: '959',        label: '959',        type: 'standalone' },
  { slug: 'carrera-gt', label: 'Carrera GT', type: 'standalone' },
  { slug: '918-spyder', label: '918 Spyder', type: 'standalone' },
]

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
  '911':    ['F-Body', 'G-Body', '964', '993', '996', '997', '991', '992'],
  'cayman': ['987', '981', '718'],
  'boxster': ['986', '987', '981', '718'],
}

export const VARIANTS = {
  '911': {
    'F-Body': [
      '911', '911S', '911T', '911E', '911L', '911R',
      'Carrera RS 2.7', 'Carrera RS 2.7 Lightweight', 'S/T',
    ],
    'G-Body': [
      'Speedster', 'Turbo 3.3 Slant Nose', '930 Turbo',
      'Carrera 2.7 MFI', 'Carrera 2.7', 'Carrera 3.2', 'SC', '911S', '911',
    ],
    '964': [
      'Carrera', 'Carrera RS', 'RS America',
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
}

// Hero image filename (served from /images/variants/) for each variant.
// All variants within a generation share the same photo for now; add a
// more-specific key to override an individual variant later.
const _h = (variants, img) => Object.fromEntries(variants.map(v => [v, img]))

export const VARIANT_HERO = {
  '911': {
    'F-Body': _h(VARIANTS['911']['F-Body'], 'fseries.jpeg'),
    'G-Body':   _h(VARIANTS['911']['G-Body'],   'gbody.jpg'),
    '964':      _h(VARIANTS['911']['964'],       '964.jpeg'),
    '993':      _h(VARIANTS['911']['993'],       '993.jpg'),
    '996.1':    _h(VARIANTS['911']['996.1'],     '996.jpeg'),
    '996.2':    _h(VARIANTS['911']['996.2'],     '996.jpeg'),
    '997.1':    _h(VARIANTS['911']['997.1'],     '997.jpg'),
    '997.2':    _h(VARIANTS['911']['997.2'],     '997.jpg'),
    '991.1':    _h(VARIANTS['911']['991.1'],     '991.jpeg'),
    '991.2':    _h(VARIANTS['911']['991.2'],     '991.jpeg'),
    '992.1':    _h(VARIANTS['911']['992.1'],     '992.jpeg'),
    '992.2':    _h(VARIANTS['911']['992.2'],     '992.jpeg'),
  },
  // Cayman and Boxster: no generation-specific photos yet; add filenames to unlock
  'cayman':  {},
  'boxster':  {},
}

// Hero image for standalone models (no generation/variant hierarchy)
export const MODEL_HERO = {
  '959':        '959.jpg',
  'carrera-gt': 'carrera-gt.jpeg',
  '918-spyder': '918.jpeg',
}

// Hero image for generation-level pages (VariantIndex).
// Full Vite public-directory paths so no runtime path construction is needed.
export const GENERATION_HERO = {
  '911': {
    'F-Body': '/images/fseries.jpeg',
    'G-Body':   '/images/gbody.jpg',
    '964':      '/images/964.jpeg',
    '993':      '/images/993.jpg',
    '996':      '/images/996.jpeg',
    '996.1':    '/images/996.jpeg',
    '996.2':    '/images/996.jpeg',
    '997':      '/images/997.jpg',
    '997.1':    '/images/997.jpg',
    '997.2':    '/images/997.jpg',
    '991':      '/images/991.jpeg',
    '991.1':    '/images/991.jpeg',
    '991.2':    '/images/991.jpeg',
    '992':      '/images/992.jpeg',
    '992.1':    '/images/992.jpeg',
    '992.2':    '/images/992.jpeg',
  },
}
