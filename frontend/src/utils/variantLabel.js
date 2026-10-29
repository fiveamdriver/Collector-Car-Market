// Display name for a variant. The DB stores the bare trim ("base", "S", "GT4"),
// but for models whose trims aren't names on their own, the card should carry
// the model: "Boxster", "Boxster S", "Cayman GT4", "944 Turbo".
// 911 trims already read as names ("Carrera S", "GT3") and 911 Race and 356
// keep theirs as-is, so those fall through unchanged.
const PREFIXED = new Set(['boxster', 'cayman', '924', '944', '968', '928'])

export function variantLabel(model, variant) {
  if (!PREFIXED.has(model.slug)) return variant
  if (variant === 'base') return model.label
  return variant.includes(model.label) ? variant : `${model.label} ${variant}`
}
