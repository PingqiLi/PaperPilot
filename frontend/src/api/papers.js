import api from './client'

export async function getPaper(id) {
  const { data } = await api.get(`/papers/${id}`)
  return data
}
