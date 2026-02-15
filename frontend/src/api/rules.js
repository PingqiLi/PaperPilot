import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    timeout: 30000,
})

// 获取规则配置
export async function fetchRules() {
    const { data } = await api.get('/rules')
    return data
}

// 更新规则配置
export async function updateRules(rules) {
    const { data } = await api.put('/rules', { rules })
    return data
}

// 获取ArXiv分类列表
export async function fetchCategories() {
    const { data } = await api.get('/rules/categories')
    return data
}
