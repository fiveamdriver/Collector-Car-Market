export function toSlug(str) {
  return str
    .toLowerCase()
    .replace(/[\s./]+/g, '-')  // spaces, dots, slashes → hyphens
    .replace(/-+/g, '-')        // collapse consecutive hyphens
    .replace(/^-|-$/g, '')      // trim leading/trailing hyphens
}

// Find the canonical display name for a slug from a list of candidates.
export function fromSlug(slug, candidates) {
  return candidates?.find(v => toSlug(v) === slug) ?? null
}
