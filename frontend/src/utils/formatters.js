export function fmtVal(n) {
  return n ? `$${n.toLocaleString()}` : '—'
}
