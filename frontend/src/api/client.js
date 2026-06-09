import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000/api/v1' })

export async function fetchAuctionResults(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  )
  const { data } = await api.get('/auction-results', { params: clean })
  return data
}
