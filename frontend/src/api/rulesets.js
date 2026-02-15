/**
 * 规则集API服务
 */
import axios from 'axios'

const API_BASE = '/api/v1'

/**
 * 获取所有规则集
 */
export async function getRulesets() {
    const response = await axios.get(`${API_BASE}/rulesets`)
    return response.data
}

/**
 * 创建规则集
 */
export async function createRuleset(data) {
    const response = await axios.post(`${API_BASE}/rulesets`, data)
    return response.data
}

/**
 * 更新规则集
 */
export async function updateRuleset(id, data) {
    const response = await axios.put(`${API_BASE}/rulesets/${id}`, data)
    return response.data
}

/**
 * 删除规则集
 */
export async function deleteRuleset(id) {
    const response = await axios.delete(`${API_BASE}/rulesets/${id}`)
    return response.data
}

/**
 * 获取规则集下的论文列表
 */
export async function getRulesetPapers(rulesetId, params = {}) {
    const { page = 1, page_size = 20, sort_by = 'semantic_score', sort_order = 'desc', min_score = 0 } = params
    const response = await axios.get(`${API_BASE}/rulesets/${rulesetId}/papers`, {
        params: { page, page_size, sort_by, sort_order, min_score }
    })
    return response.data
}

/**
 * 触发规则集抓取
 */
export async function triggerRulesetFetch(rulesetId) {
    const response = await axios.post(`${API_BASE}/rulesets/${rulesetId}/fetch`)
    return response.data
}

/**
 * 触发规则集LLM评分
 */
export async function triggerRulesetScore(rulesetId, batchSize = 10) {
    const response = await axios.post(`${API_BASE}/rulesets/${rulesetId}/score`, null, {
        params: { batch_size: batchSize }
    })
    return response.data
}

/**
 * 获取规则集统计信息
 */
export async function getRulesetStats(rulesetId) {
    const response = await axios.get(`${API_BASE}/rulesets/${rulesetId}/stats`)
    return response.data
}

/**
 * 更新规则集论文引用数
 */
export async function updateRulesetCitations(rulesetId, limit = 50) {
    const response = await axios.post(`${API_BASE}/rulesets/${rulesetId}/update-citations`, null, {
        params: { limit }
    })
    return response.data
}

/**
 * 触发历史精选收集（Collect阶段）
 */
export async function triggerCollect(rulesetId) {
    const response = await axios.post(`${API_BASE}/rulesets/${rulesetId}/collect`)
    return response.data
}

/**
 * 触发追踪新论文（Track阶段）
 */
export async function triggerTrack(rulesetId) {
    const response = await axios.post(`${API_BASE}/rulesets/${rulesetId}/track`)
    return response.data
}
/**
 * 触发快速筛选 (Rapid Screening)
 */
export async function triggerRapidScreening(rulesetId, maxResults = 20) {
    const response = await axios.post(`${API_BASE}/rulesets/${rulesetId}/rapid-screening`, null, {
        params: { max_results: maxResults }
    })
    return response.data
}

export default {
    getRulesets,
    createRuleset,
    updateRuleset,
    deleteRuleset,
    getRulesetPapers,
    getRulesetStats,
    triggerRulesetFetch,
    triggerRulesetScore,
    updateRulesetCitations,
    triggerCollect,
    triggerTrack,
    triggerRapidScreening
}
