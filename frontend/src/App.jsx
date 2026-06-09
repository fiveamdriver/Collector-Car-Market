import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom'
import { ALL_MODELS } from './data/taxonomy'
import Layout from './components/Layout'
import MarketHome from './pages/MarketHome'
import GenerationIndex from './pages/GenerationIndex'
import VariantIndex from './pages/VariantIndex'
import MarketDetail from './pages/MarketDetail'
import './App.css'

// /:modelSlug — routes to GenerationIndex for series models, MarketDetail for standalone
function ModelRouter() {
  const { modelSlug } = useParams()
  const model = ALL_MODELS.find(m => m.slug === modelSlug)
  if (!model) return <Navigate to="/" replace />
  return model.type === 'standalone' ? <MarketDetail /> : <GenerationIndex />
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/"                                    element={<MarketHome />} />
          <Route path="/:modelSlug"                          element={<ModelRouter />} />
          <Route path="/:modelSlug/:generation"              element={<VariantIndex />} />
          <Route path="/:modelSlug/:generation/:variantSlug" element={<MarketDetail />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
