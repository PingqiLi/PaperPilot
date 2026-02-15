import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import rulesetsApi from '../api/rulesets'
import './RuleSetEditor.css'

// ArXiv常用分类
const ARXIV_CATEGORIES = [
    { value: 'cs.AI', label: 'cs.AI - 人工智能' },
    { value: 'cs.LG', label: 'cs.LG - 机器学习' },
    { value: 'cs.CL', label: 'cs.CL - 自然语言处理' },
    { value: 'cs.CV', label: 'cs.CV - 计算机视觉' },
    { value: 'cs.NE', label: 'cs.NE - 神经网络' },
    { value: 'cs.IR', label: 'cs.IR - 信息检索' },
    { value: 'stat.ML', label: 'stat.ML - 统计机器学习' },
]

// 预设规则集模板
const PRESET_TEMPLATES = {
    "AI量化算法": {
        description: "LLM量化推理优化技术",
        topic_description: "关注大语言模型(LLM)的量化技术，特别是针对推理加速的方法。包括权重量化(Weight Quantization)、激活值量化(Activation Quantization)、KV Cache量化等。重点关注低比特(INT4/INT8)下的精度保持技术、混合精度策略以及在边缘设备或特定硬件(GPU/NPU)上的部署优化。",
        categories: ["cs.LG", "cs.AI", "cs.CL"],
        keywords_include: [
            "quantization", "quantized", "low-bit", "INT8", "INT4", "FP8",
            "GPTQ", "AWQ", "SmoothQuant", "ZeroQuant", "LLM.int8",
            "weight quantization", "activation quantization",
            "PTQ", "QAT", "mixed precision"
        ],
        keywords_exclude: ["survey", "review", "tutorial", "introduction to"],
        semantic_query: "LLM quantization techniques for inference acceleration",
        date_range_days: 90,
    },
    "注意力机制": {
        description: "高效注意力计算和优化",
        topic_description: "关注Transformer架构中的注意力机制优化。特别是旨在降低计算复杂度(如线性注意力)、减少显存占用(如FlashAttention、PagedAttention)以及提升长序列处理能力的技术。也包括稀疏注意力(Sparse Attention)和针对特定硬件的算子优化。",
        categories: ["cs.LG", "cs.CL", "cs.CV"],
        keywords_include: [
            "attention", "transformer", "FlashAttention", "linear attention",
            "sparse attention", "efficient attention", "multi-head attention",
            "KV cache", "sliding window"
        ],
        keywords_exclude: ["survey", "review"],
        semantic_query: "Efficient attention mechanisms and transformer optimization",
        date_range_days: 60,
    },
    "推理优化": {
        description: "LLM推理加速和优化技术",
        topic_description: "关注大语言模型的推理加速技术。包括投机采样(Speculative Decoding)、剪枝(Pruning)、蒸馏(Distillation)、模型并行(Model Parallelism)、流水线并行(Pipeline Parallelism)以及高效的Serving系统设计(如vLLM, TGI)。",
        categories: ["cs.LG", "cs.AI", "cs.CL"],
        keywords_include: [
            "inference", "acceleration", "optimization", "speculative decoding",
            "pruning", "distillation", "TensorRT", "vLLM", "serving",
            "latency", "throughput", "batching"
        ],
        keywords_exclude: ["survey", "review", "tutorial"],
        semantic_query: "LLM inference optimization, serving, and acceleration techniques",
        date_range_days: 60,
    }
}

export default function RuleSetEditor() {
    const navigate = useNavigate()
    const { id } = useParams()
    const isEdit = !!id

    const [formData, setFormData] = useState({
        name: '',
        description: '',
        topic_description: '',
        categories: [],
        keywords_include: [],
        keywords_exclude: [],
        semantic_query: '',
        date_range_days: 30,
    })
    const [newKeyword, setNewKeyword] = useState('')
    const [newExcludeKeyword, setNewExcludeKeyword] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    useEffect(() => {
        if (isEdit) {
            console.log("Loading ruleset for edit mode")
            loadRuleset()
        }
    }, [id])

    const loadRuleset = async () => {
        try {
            const data = await rulesetsApi.getRulesets()
            const ruleset = data.find(r => r.id === parseInt(id))
            if (ruleset) {
                setFormData({
                    name: ruleset.name || '',
                    description: ruleset.description || '',
                    topic_description: ruleset.topic_description || '',
                    categories: ruleset.categories || [],
                    keywords_include: ruleset.keywords_include || [],
                    keywords_exclude: ruleset.keywords_exclude || [],
                    semantic_query: ruleset.semantic_query || '',
                    date_range_days: ruleset.date_range_days || 30,
                })
            }
        } catch (err) {
            setError('加载规则集失败')
        }
    }


    const handleCategoryChange = (category) => {
        setFormData(prev => ({
            ...prev,
            categories: prev.categories.includes(category)
                ? prev.categories.filter(c => c !== category)
                : [...prev.categories, category]
        }))
    }

    const addKeyword = (type) => {
        const keyword = type === 'include' ? newKeyword.trim() : newExcludeKeyword.trim()
        if (!keyword) return

        const field = type === 'include' ? 'keywords_include' : 'keywords_exclude'
        if (!formData[field].includes(keyword)) {
            setFormData(prev => ({
                ...prev,
                [field]: [...prev[field], keyword]
            }))
        }
        type === 'include' ? setNewKeyword('') : setNewExcludeKeyword('')
    }

    const removeKeyword = (type, keyword) => {
        const field = type === 'include' ? 'keywords_include' : 'keywords_exclude'
        setFormData(prev => ({
            ...prev,
            [field]: prev[field].filter(k => k !== keyword)
        }))
    }

    const applyTemplate = (templateName) => {
        const template = PRESET_TEMPLATES[templateName]
        if (template) {
            setFormData({
                name: templateName,
                ...template
            })
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setError('')

        try {
            if (isEdit) {
                await rulesetsApi.updateRuleset(id, formData)
            } else {
                await rulesetsApi.createRuleset(formData)
            }
            navigate('/')
        } catch (err) {
            setError(err.response?.data?.detail || '保存失败')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="ruleset-editor">
            <header className="editor-header">
                <h1>{isEdit ? '编辑规则集' : '创建规则集'}</h1>
                <p>配置论文筛选规则，包括分类、关键词和语义搜索</p>
            </header>

            {/* 预设模板 */}
            {!isEdit && (
                <div className="templates-section">
                    <h3>📋 快速选择预设模板</h3>
                    <div className="template-buttons">
                        {Object.keys(PRESET_TEMPLATES).map(name => (
                            <button
                                key={name}
                                type="button"
                                className="template-btn"
                                onClick={() => applyTemplate(name)}
                            >
                                {name}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            <form onSubmit={handleSubmit} className="editor-form">
                {/* 基本信息 */}
                <div className="form-section">
                    <h3>基本信息</h3>
                    <div className="form-field">
                        <label>名称 *</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                            placeholder="如：AI量化算法"
                            required
                        />
                    </div>
                    <div className="form-field">
                        <label>描述</label>
                        <input
                            type="text"
                            value={formData.description}
                            onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                            placeholder="简短描述这个规则集的目的"
                        />
                    </div>
                </div>

                {/* ArXiv分类 */}
                <div className="form-section">
                    <h3>📚 ArXiv分类</h3>
                    <div className="category-grid">
                        {ARXIV_CATEGORIES.map(cat => (
                            <label key={cat.value} className="category-checkbox">
                                <input
                                    type="checkbox"
                                    checked={formData.categories.includes(cat.value)}
                                    onChange={() => handleCategoryChange(cat.value)}
                                />
                                <span>{cat.label}</span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* 包含关键词 */}
                <div className="form-section">
                    <h3>🔍 包含关键词</h3>
                    <p className="hint">论文标题或摘要必须包含这些关键词之一</p>
                    <div className="keyword-input">
                        <input
                            type="text"
                            value={newKeyword}
                            onChange={e => setNewKeyword(e.target.value)}
                            placeholder="输入关键词"
                            onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addKeyword('include'))}
                        />
                        <button type="button" onClick={() => addKeyword('include')}>添加</button>
                    </div>
                    <div className="keyword-tags">
                        {formData.keywords_include.map(kw => (
                            <span key={kw} className="tag include">
                                {kw}
                                <button type="button" onClick={() => removeKeyword('include', kw)}>×</button>
                            </span>
                        ))}
                    </div>
                </div>

                {/* 排除关键词 */}
                <div className="form-section">
                    <h3>🚫 排除关键词</h3>
                    <p className="hint">包含这些词的论文会被过滤掉</p>
                    <div className="keyword-input">
                        <input
                            type="text"
                            value={newExcludeKeyword}
                            onChange={e => setNewExcludeKeyword(e.target.value)}
                            placeholder="输入要排除的关键词"
                            onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addKeyword('exclude'))}
                        />
                        <button type="button" onClick={() => addKeyword('exclude')}>添加</button>
                    </div>
                    <div className="keyword-tags">
                        {formData.keywords_exclude.map(kw => (
                            <span key={kw} className="tag exclude">
                                {kw}
                                <button type="button" onClick={() => removeKeyword('exclude', kw)}>×</button>
                            </span>
                        ))}
                    </div>
                </div>

                {/* 语义搜索 */}
                <div className="form-section">
                    <h3>🧠 语义搜索与Agent筛选</h3>

                    <div className="form-field">
                        <label>Agent筛选描述 (Topic Description) *</label>
                        <p className="hint">这是最重要的配置！请详细描述你的研究Topic。OpenClaw Agent 将使用这段描述来通过"阅读"论文摘要进行评分。请使用自然语言（建议中文）。</p>
                        <textarea
                            value={formData.topic_description}
                            onChange={e => setFormData(prev => ({ ...prev, topic_description: e.target.value }))}
                            placeholder="例如：关注大语言模型(LLM)的量化技术，特别是针对推理加速的方法。包括权重量化、激活值量化等..."
                            rows={5}
                            required
                        />
                    </div>

                    <div className="form-field" style={{ marginTop: '15px' }}>
                        <label>S2 语义搜索查询 (Semantic Query)</label>
                        <p className="hint">用于Semantic Scholar API的简短英文搜索语句（可选，若为空将使用Topic自动生成）</p>
                        <textarea
                            value={formData.semantic_query}
                            onChange={e => setFormData(prev => ({ ...prev, semantic_query: e.target.value }))}
                            placeholder="例如：LLM quantization techniques for inference acceleration"
                            rows={2}
                        />
                    </div>
                </div>

                {/* 时间范围 */}
                <div className="form-section">
                    <h3>📅 时间范围</h3>
                    <div className="form-field inline">
                        <label>抓取过去</label>
                        <input
                            type="number"
                            value={formData.date_range_days}
                            onChange={e => setFormData(prev => ({ ...prev, date_range_days: parseInt(e.target.value) || 30 }))}
                            min={7}
                            max={730}
                            style={{ width: '80px' }}
                        />
                        <span>天的论文</span>
                    </div>
                </div>

                {error && <div className="error-message">{error}</div>}

                <div className="form-actions">
                    <button type="button" className="btn-cancel" onClick={() => navigate('/')}>
                        取消
                    </button>
                    <button type="submit" className="btn-save" disabled={loading}>
                        {loading ? '保存中...' : (isEdit ? '更新规则集' : '创建规则集')}
                    </button>
                </div>
            </form>
        </div>
    )
}
