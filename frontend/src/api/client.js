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

// Counts/averages/trend lines computed in the database. Index pages render only
// aggregates, so this replaces pulling every matching row into the browser.
export async function fetchAggregateStats(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  )
  const { data } = await api.get('/stats/aggregate', { params: clean })
  return data
}

export async function fetchActiveListings(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  )
  const { data } = await api.get('/active-listings', { params: clean })
  return data
}
