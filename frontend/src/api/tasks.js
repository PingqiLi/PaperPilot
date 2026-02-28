import api from './client'

export async function getTasks(params = {}) {
  const { data } = await api.get('/tasks', { params })
  return data
}

export async function getTask(taskId) {
  const { data } = await api.get(`/tasks/${taskId}`)
  return data
}

export async function retryTask(taskId) {
  const { data } = await api.post(`/tasks/${taskId}/retry`)
  return data
}
