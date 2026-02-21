import api from './client'

export async function generateDraft(topicSentence) {
  const { data } = await api.post('/rulesets/draft', { topic_sentence: topicSentence })
  return data
}

export async function getGlobalPapers(params = {}) {
  const { data } = await api.get('/papers', { params })
  return data
}

export async function getRulesets() {
  const { data } = await api.get('/rulesets')
  return data
}

export async function getTopicOverview() {
  const { data } = await api.get('/rulesets/overview')
  return data
}

export async function createRuleset(payload) {
  const { data } = await api.post('/rulesets', payload)
  return data
}

export async function getRuleset(id) {
  const { data } = await api.get(`/rulesets/${id}`)
  return data
}

export async function updateRuleset(id, payload) {
  const { data } = await api.put(`/rulesets/${id}`, payload)
  return data
}

export async function deleteRuleset(id) {
  const { data } = await api.delete(`/rulesets/${id}`)
  return data
}

export async function getReinitPreview(rulesetId) {
  const { data } = await api.get(`/rulesets/${rulesetId}/reinit-preview`)
  return data
}

export async function createRun(rulesetId, runType, { reinit = false } = {}) {
  const { data } = await api.post(`/rulesets/${rulesetId}/runs`, { run_type: runType, reinit })
  return data
}

export async function getRuns(rulesetId) {
  const { data } = await api.get(`/rulesets/${rulesetId}/runs`)
  return data
}

export async function getRun(rulesetId, runId) {
  const { data } = await api.get(`/rulesets/${rulesetId}/runs/${runId}`)
  return data
}

export async function getRulesetPapers(rulesetId, params = {}) {
  const { data } = await api.get(`/rulesets/${rulesetId}/papers`, { params })
  return data
}

export async function updatePaperStatus(rulesetId, paperId, status) {
  const { data } = await api.patch(`/rulesets/${rulesetId}/papers/${paperId}/status`, { status })
  return data
}

export async function getDigests(rulesetId, params = {}) {
  const { data } = await api.get(`/rulesets/${rulesetId}/digests`, { params })
  return data
}

export async function createDigest(rulesetId, digestType) {
  const { data } = await api.post(`/rulesets/${rulesetId}/digests`, { digest_type: digestType })
  return data
}

export async function getDigest(rulesetId, digestId) {
  const { data } = await api.get(`/rulesets/${rulesetId}/digests/${digestId}`)
  return data
}

export async function exportDigestMarkdown(rulesetId, digestId) {
  const { data } = await api.get(`/rulesets/${rulesetId}/digests/${digestId}/markdown`, {
    responseType: 'blob',
  })
  return data
}

export async function bulkUpdatePaperStatus(rulesetId, paperIds, status) {
  const { data } = await api.patch(`/rulesets/${rulesetId}/papers/bulk-status`, {
    paper_ids: paperIds,
    status,
  })
  return data
}

export async function exportBibtex(rulesetId, status) {
  const params = status ? { status } : {}
  const { data } = await api.get(`/rulesets/${rulesetId}/papers/bibtex`, {
    params,
    responseType: 'blob',
  })
  return data
}

export async function getPaperDetail(rulesetId, paperId) {
  const { data } = await api.get(`/rulesets/${rulesetId}/papers/${paperId}`)
  return data
}

export async function analyzePaper(rulesetId, paperId) {
  const { data } = await api.post(`/rulesets/${rulesetId}/papers/${paperId}/analyze`)
  return data
}

export async function addPaperToTopic(rulesetId, identifier) {
  const { data } = await api.post(`/rulesets/${rulesetId}/papers/add`, { identifier })
  return data
}

export async function reorderTopics(payload) {
  const { data } = await api.put('/rulesets/reorder', payload)
  return data
}
