import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    timeout: 30000,
})

// 获取论文列表
export async function fetchPapers(params = {}) {
    const { data } = await api.get('/papers', { params })
    return data
}

// 获取论文详情
export async function fetchPaper(id) {
    const { data } = await api.get(`/papers/${id}`)
    return data
}

// 更新论文（收藏、已读等）
export async function updatePaper(id, updates) {
    const { data } = await api.patch(`/papers/${id}`, updates)
    return data
}

// 触发抓取
export async function triggerFetch() {
    const { data } = await api.post('/papers/fetch')
    return data
}

// 处理单篇论文
export async function processPaper(id) {
    const { data } = await api.post(`/papers/${id}/process`)
    return data
}

// 获取抓取状态
export async function fetchStatus() {
    const { data } = await api.get('/papers/status')
    return data
}
