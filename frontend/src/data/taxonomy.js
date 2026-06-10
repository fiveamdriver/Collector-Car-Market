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

export const GENERATIONS = {
  '911':    ['F-Series', 'G-Series', '964', '993', '996.1', '996.2', '997.1', '997.2', '991.1', '991.2', '992'],
  'cayman': ['987', '981', '718'],
  'boxster': ['986', '987', '981', '718'],
}

export const VARIANTS = {
  '911': {
    'F-Series': [
      '911', '911S', '911T', '911E', '911L', '911R',
      'Carrera RS 2.7', 'Carrera RS 2.7 Lightweight', 'S/T',
    ],
    'G-Series': [
      'Carrera 2.7', '911S', 'Carrera RS 3.0', 'SC', 'Carrera 3.2',
      'Turbo 3.0', 'Turbo 3.3', 'Turbo 3.3 Slant Nose', 'Turbo S', 'Speedster',
    ],
    '964': [
      'Carrera', 'Carrera RS', 'Carrera RS America',
      'Turbo', 'Turbo S', 'Speedster', 'GTS',
    ],
    '993': [
      'Carrera', 'Carrera S', 'Carrera RS',
      'Turbo', 'Turbo S', 'GT2', 'Speedster', 'GTS',
    ],
    '996.1': ['Carrera', 'Turbo', 'GT3'],
    '996.2': ['Carrera', 'Carrera S', 'Turbo', 'Turbo S', 'GT3', 'GT3 RS', 'GT2'],
    '997.1': [
      'Carrera', 'Carrera S',
      'Turbo', 'GT3', 'GT3 RS', 'GT2', 'Sport Classic',
    ],
    '997.2': [
      'Carrera', 'Carrera S', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'GT3 RS 4.0', 'GT2 RS', 'Speedster',
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
    '992': [
      'Carrera', 'Carrera S', 'Carrera T', 'Carrera GTS',
      'Turbo', 'Turbo S',
      'GT3', 'GT3 RS', 'GT2 RS', 'S/T', 'Sport Classic', 'Dakar',
    ],
  },
  'cayman': {
    '987': ['base', 'S', 'R', 'GTS'],
    '981': ['base', 'S', 'GTS', 'GT4'],
    '718': ['base', 'S', 'GTS', 'GT4', 'GT4 RS'],
  },
  'boxster': {
    '986': ['base', 'S'],
    '987': ['base', 'S', 'Spyder', 'GTS'],
    '981': ['base', 'S', 'GTS', 'Spyder'],
    '718': ['base', 'S', 'GTS', 'Spyder', 'RS Spyder'],
  },
}
