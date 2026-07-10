import { Suspense, lazy } from 'react'

// PriceHistoryChart is the only recharts consumer; loading it on demand keeps
// the recharts + d3 dependency tree out of the main bundle, which every route
// (including the chartless home page) otherwise pays for.
const PriceHistoryChart = lazy(() => import('./PriceHistoryChart'))

export default function LazyPriceHistoryChart(props) {
  return (
    <Suspense fallback={<div className="price-chart" />}>
      <PriceHistoryChart {...props} />
    </Suspense>
  )
}
