import api from './client'

export async function getSettings() {
  const { data } = await api.get('/settings')
  return data
}

export async function updateSettings(updates) {
  const { data } = await api.put('/settings', updates)
  return data
}

export async function getEmailLogs(params = {}) {
  const { data } = await api.get('/settings/emails', { params })
  return data
}

export async function sendTestEmail() {
  const { data } = await api.post('/settings/emails/test')
  return data
}

export async function getPromptDefaults() {
  const { data } = await api.get('/settings/prompts/defaults')
  return data
}
