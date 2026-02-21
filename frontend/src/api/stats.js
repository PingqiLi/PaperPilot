import api from './client'

export async function getCostStats() {
  const { data } = await api.get('/stats/costs')
  return data
}

export async function getDailyCosts(days = 10) {
  const { data } = await api.get('/stats/costs/daily', { params: { days } })
  return data
}

export async function getRequestHistory(params = {}) {
  const { data } = await api.get('/stats/costs/requests', { params })
  return data
}
