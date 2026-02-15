import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, Info } from 'lucide-react'
import { fetchRules, updateRules } from '../api/rules'
import './RulesConfig.css'

function RulesConfig() {
    const queryClient = useQueryClient()
    const [localRules, setLocalRules] = useState(null)

    const { data: rules, isLoading } = useQuery({
        queryKey: ['rules'],
        queryFn: fetchRules,
        onSuccess: (data) => {
            if (!localRules) setLocalRules(data)
        }
    })

    const saveMutation = useMutation({
        mutationFn: () => updateRules(localRules),
        onSuccess: () => {
            queryClient.invalidateQueries(['rules'])
        }
    })

    // 初始化本地状态
    if (!localRules && rules) {
        setLocalRules(rules)
    }

    if (isLoading || !localRules) {
        return (
            <div className="loading-state">
                <div className="loading-spinner"></div>
                <p>加载中...</p>
            </div>
        )
    }

    const updateField = (path, value) => {
        const newRules = { ...localRules }
        const keys = path.split('.')
        let obj = newRules
        for (let i = 0; i < keys.length - 1; i++) {
            if (!obj[keys[i]]) obj[keys[i]] = {}
            obj = obj[keys[i]]
        }
        obj[keys[keys.length - 1]] = value
        setLocalRules(newRules)
    }

    return (
        <div className="rules-config-page fade-in">
            <header className="page-header">
                <div>
                    <h1 className="page-title">⚙️ 全局设置</h1>
                    <p className="page-subtitle">配置LLM评分和系统参数</p>
                </div>
                <button
                    className="btn btn-primary"
                    onClick={() => saveMutation.mutate()}
                    disabled={saveMutation.isPending}
                >
                    <Save size={18} />
                    {saveMutation.isPending ? '保存中...' : '保存设置'}
                </button>
            </header>

            <div className="config-sections">
                {/* LLM配置 */}
                <section className="config-section card">
                    <h2 className="section-title">
                        🤖 LLM配置
                        <span className="title-hint">
                            <Info size={16} />
                            用于论文评分的大模型设置
                        </span>
                    </h2>

                    <div className="settings-grid">
                        <div className="setting-item full-width">
                            <label>
                                <span>Semantic Scholar API Key（可选）</span>
                                <input
                                    type="password"
                                    className="input"
                                    placeholder="申请地址: semanticscholar.org/product/api"
                                    value={localRules.s2_api_key || ''}
                                    onChange={(e) => updateField('s2_api_key', e.target.value)}
                                />
                            </label>
                            <p className="setting-hint">有API Key可以稳定获取论文引用数</p>
                        </div>

                        <div className="setting-item">
                            <label className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={localRules.cost?.prefer_local_llm || false}
                                    onChange={(e) => updateField('cost.prefer_local_llm', e.target.checked)}
                                />
                                <span>优先使用本地LLM</span>
                            </label>
                        </div>
                    </div>
                </section>

                {/* 评分设置 */}
                <section className="config-section card">
                    <h2 className="section-title">⭐ 评分设置</h2>

                    <div className="settings-grid">
                        <div className="setting-item">
                            <label>
                                <span>评分阈值 (1-10)</span>
                                <input
                                    type="number"
                                    className="input"
                                    min={1}
                                    max={10}
                                    value={localRules.advanced?.score_threshold || 5}
                                    onChange={(e) => updateField('advanced.score_threshold', Number(e.target.value))}
                                />
                            </label>
                            <p className="setting-hint">低于该分数的论文不会高亮显示</p>
                        </div>

                        <div className="setting-item">
                            <label>
                                <span>默认收集天数</span>
                                <input
                                    type="number"
                                    className="input"
                                    min={30}
                                    max={1095}
                                    value={localRules.collect_range_days || 1095}
                                    onChange={(e) => updateField('collect_range_days', Number(e.target.value))}
                                />
                            </label>
                            <p className="setting-hint">历史精选收集的时间范围</p>
                        </div>
                    </div>
                </section>

                {/* 研究兴趣 */}
                <section className="config-section card">
                    <h2 className="section-title">
                        📝 研究兴趣描述
                        <span className="title-hint">
                            <Info size={16} />
                            用于所有规则集的LLM评分Prompt
                        </span>
                    </h2>
                    <textarea
                        className="input interests-input"
                        placeholder="描述你的研究兴趣，例如：&#10;我对大模型推理优化、量化压缩、注意力机制改进相关的论文感兴趣。&#10;特别关注在NPU/GPU上的部署优化工作。"
                        value={localRules.interests || ''}
                        onChange={(e) => updateField('interests', e.target.value)}
                        rows={5}
                    />
                </section>
            </div>
        </div>
    )
}

export default RulesConfig
