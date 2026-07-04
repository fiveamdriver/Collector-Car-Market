import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL })

export async function fetchAuctionResults(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  )
  const { data } = await api.get('/auction-results', { params: clean })
  return data
}

export async function fetchModelLineStats() {
  const { data } = await api.get('/stats/model-lines')
  return data
}

export async function fetchActiveListings(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  )
  const { data } = await api.get('/active-listings', { params: clean })
  return data
}
