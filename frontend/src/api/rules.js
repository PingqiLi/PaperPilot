import api from './client'

export async function getCategories() {
  const { data } = await api.get('/rules/categories')
  return data
}
