import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom'
import { ALL_MODELS, GENERATION_GROUPS } from './data/taxonomy'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import MarketHome from './pages/MarketHome'
import GenerationIndex from './pages/GenerationIndex'
import GroupIndex from './pages/GroupIndex'
import VariantModelIndex from './pages/VariantModelIndex'
import SubGenerationIndex from './pages/SubGenerationIndex'
import VariantIndex from './pages/VariantIndex'
import MarketDetail from './pages/MarketDetail'
import './App.css'

function ModelRouter() {
  const { modelSlug } = useParams()
  const model = ALL_MODELS.find(m => m.slug === modelSlug)
  if (!model) return <Navigate to="/" replace />
  if (model.type === 'group')         return <GroupIndex />
  if (model.type === 'variant-model') return <VariantModelIndex />
  if (model.type === 'standalone')    return <MarketDetail />
  return <GenerationIndex />
}

// /:modelSlug/:seg1 — variant-model leaf (944/turbo) → MarketDetail;
// group slug (997) → SubGenerationIndex; flat gen (964) → VariantIndex
function Seg1Router() {
  const { modelSlug, seg1 } = useParams()
  const model = ALL_MODELS.find(m => m.slug === modelSlug)
  if (!model) return <Navigate to="/" replace />
  if (model.type === 'variant-model') return <MarketDetail />
  const groups = GENERATION_GROUPS[modelSlug] ?? {}
  // Object.hasOwn, not `in`: `in` walks the prototype chain, so a URL segment
  // like /911/constructor would match Object.prototype and mis-route.
  return Object.hasOwn(groups, seg1) ? <SubGenerationIndex /> : <VariantIndex />
}

// /:modelSlug/:seg1/:seg2 — group+subgen (997/997.1) → VariantIndex; gen+variant (964/carrera) → MarketDetail
function Seg2Router() {
  const { modelSlug, seg1, seg2 } = useParams()
  const model = ALL_MODELS.find(m => m.slug === modelSlug)
  if (!model) return <Navigate to="/" replace />
  const groups = GENERATION_GROUPS[modelSlug] ?? {}
  return groups[seg1]?.includes(seg2) ? <VariantIndex /> : <MarketDetail />
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <ErrorBoundary>
          <Routes>
            <Route path="/"                                element={<MarketHome />} />
            <Route path="/:modelSlug"                      element={<ModelRouter />} />
            <Route path="/:modelSlug/:seg1"                element={<Seg1Router />} />
            <Route path="/:modelSlug/:seg1/:seg2"          element={<Seg2Router />} />
            <Route path="/:modelSlug/:seg1/:seg2/:seg3"    element={<MarketDetail />} />
          </Routes>
        </ErrorBoundary>
      </Layout>
    </BrowserRouter>
  )
}
