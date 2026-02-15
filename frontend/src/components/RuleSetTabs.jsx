import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import rulesetsApi from '../api/rulesets'
import { updatePaper } from '../api/papers'
import './RuleSetTabs.css'

/**
 * 规则集Tab组件
 * 支持多规则集切换、排序和论文列表展示
 */
export default function RuleSetTabs({ onPaperSelect }) {
    const [rulesets, setRulesets] = useState([])
    const [activeRulesetId, setActiveRulesetId] = useState(null)
    const [papers, setPapers] = useState([])
    const [curatedPapers, setCuratedPapers] = useState([])  // 精选历史
    const [newPapers, setNewPapers] = useState([])  // 新论文
    const [isCollected, setIsCollected] = useState(false)  // 是否已完成收集
    const [loading, setLoading] = useState(false)
    const [sortBy, setSortBy] = useState('combined')  // combined, semantic_score, citation_count, published_date
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [fetchStatus, setFetchStatus] = useState('')  // 抓取进度提示

    // 加载规则集列表
    useEffect(() => {
        loadRulesets()
    }, [])

    // 切换规则集或排序时加载论文
    useEffect(() => {
        if (activeRulesetId) {
            loadPapers()
        }
    }, [activeRulesetId, sortBy, page])

    const loadRulesets = async () => {
        try {
            const data = await rulesetsApi.getRulesets()
            setRulesets(data)
            if (data.length > 0 && !activeRulesetId) {
                setActiveRulesetId(data[0].id)
            }
        } catch (err) {
            console.error('加载规则集失败:', err)
        }
    }

    const loadPapers = async () => {
        setLoading(true)
        try {
            const data = await rulesetsApi.getRulesetPapers(activeRulesetId, {
                page,
                page_size: 100,  // 加载更多以便分区
                sort_by: sortBy === 'combined' ? 'semantic_score' : sortBy,
                sort_order: 'desc'
            })
            setPapers(data.items)
            setCuratedPapers(data.curated_papers || [])
            setNewPapers(data.new_papers || [])
            setIsCollected(data.is_collected || false)
            setTotal(data.total)
        } catch (err) {
            console.error('加载论文失败:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleTabClick = (rulesetId) => {
        setActiveRulesetId(rulesetId)
        setPage(1)
    }

    const handleTriggerFetch = async (rulesetId) => {
        try {
            await rulesetsApi.triggerRulesetFetch(rulesetId)
            setFetchStatus('正在抓取论文...')

            // 轮询检查进度
            const pollProgress = async () => {
                for (let i = 0; i < 30; i++) {  // 最多轮询30次，每次2秒
                    await new Promise(r => setTimeout(r, 2000))
                    try {
                        const stats = await rulesetsApi.getRulesetStats(rulesetId)
                        setFetchStatus(`已抓取 ${stats.total_papers} 篇论文...`)
                        if (stats.total_papers > 0) {
                            // 抓取完成
                            setFetchStatus(`抓取完成！共 ${stats.total_papers} 篇论文`)
                            loadPapers()
                            loadRulesets()
                            setTimeout(() => setFetchStatus(''), 3000)
                            return
                        }
                    } catch (e) {
                        console.error('轮询进度失败:', e)
                    }
                }
                setFetchStatus('抓取超时，请刷新页面')
            }
            pollProgress()
        } catch (err) {
            setFetchStatus('抓取失败: ' + err.message)
        }
    }

    const handleTriggerScore = async (rulesetId) => {
        try {
            setFetchStatus('正在进行LLM评分...')
            const result = await rulesetsApi.triggerRulesetScore(rulesetId)
            setFetchStatus(result.message)
            loadPapers()
            setTimeout(() => setFetchStatus(''), 3000)
        } catch (err) {
            setFetchStatus('评分失败: ' + err.message)
        }
    }

    // 收藏切换
    const handleToggleStar = async (paper) => {
        try {
            const updated = await updatePaper(paper.id, { is_starred: !paper.is_starred })
            setPapers(prev => prev.map(p => p.id === paper.id ? { ...p, is_starred: updated.is_starred } : p))
        } catch (err) {
            console.error('收藏失败:', err)
        }
    }

    // 标记有价值/无价值
    const handleFeedback = async (paper, feedbackType) => {
        try {
            const newFeedback = paper.feedback === feedbackType ? null : feedbackType
            await updatePaper(paper.id, { feedback: newFeedback })
            setPapers(prev => prev.map(p => p.id === paper.id ? { ...p, feedback: newFeedback } : p))
        } catch (err) {
            console.error('反馈失败:', err)
        }
    }

    // 触发历史精选收集
    const handleTriggerCollect = async (rulesetId) => {
        try {
            const result = await rulesetsApi.triggerCollect(rulesetId)
            setFetchStatus(result.message)

            // 轮询检查进度
            const pollProgress = async () => {
                for (let i = 0; i < 60; i++) {
                    await new Promise(r => setTimeout(r, 3000))
                    try {
                        const stats = await rulesetsApi.getRulesetStats(rulesetId)
                        setFetchStatus(`正在收集... ${stats.scored_papers}/${stats.total_papers} 篇已评分`)
                        if (stats.scored_papers >= stats.total_papers && stats.total_papers > 0) {
                            break
                        }
                    } catch (e) { }
                }
                loadPapers()
                loadRulesets()
                setFetchStatus('')
            }
            pollProgress()
        } catch (err) {
            setFetchStatus('收集失败: ' + err.message)
        }
    }

    // 触发追踪新论文
    const handleTriggerTrack = async (rulesetId) => {
        try {
            const result = await rulesetsApi.triggerTrack(rulesetId)
            setFetchStatus(result.message)

            // 轮询检查进度
            const pollProgress = async () => {
                for (let i = 0; i < 30; i++) {
                    await new Promise(r => setTimeout(r, 2000))
                    try {
                        const stats = await rulesetsApi.getRulesetStats(rulesetId)
                        setFetchStatus(`追踪中... ${stats.total_papers} 篇论文`)
                    } catch (e) { }
                }
                loadPapers()
                setFetchStatus('')
            }
            pollProgress()
        } catch (err) {
            setFetchStatus('追踪失败: ' + err.message)
        }
    }

    // 触发快速筛选
    const handleTriggerRapidScreening = async (rulesetId) => {
        try {
            const result = await rulesetsApi.triggerRapidScreening(rulesetId)
            setFetchStatus(result.message)

            // 轮询检查进度
            const pollProgress = async () => {
                for (let i = 0; i < 30; i++) {
                    await new Promise(r => setTimeout(r, 2000))
                    try {
                        const stats = await rulesetsApi.getRulesetStats(rulesetId)
                        setFetchStatus(`正在筛选... ${stats.scored_papers} 篇已评分 / ${stats.total_papers} 总数`)
                        // 简单判断：如果总数增加且有评分更新，视为有进展
                    } catch (e) { }
                }
                loadPapers()
                setFetchStatus('')
            }
            pollProgress()
        } catch (err) {
            setFetchStatus('筛选失败: ' + err.message)
        }
    }

    const activeRuleset = rulesets.find(r => r.id === activeRulesetId)

    return (
        <div className="ruleset-tabs-container">
            {/* Tab栏 */}
            <div className="tabs-header">
                <div className="tabs-list">
                    {rulesets.map(ruleset => (
                        <button
                            key={ruleset.id}
                            className={`tab-button ${activeRulesetId === ruleset.id ? 'active' : ''}`}
                            onClick={() => handleTabClick(ruleset.id)}
                        >
                            {ruleset.name}
                            <span className="tab-count">{ruleset.total_papers}</span>
                        </button>
                    ))}
                    <button className="tab-button add-tab" onClick={() => window.location.href = '/rulesets/new'}>
                        + 新建
                    </button>
                </div>

                {/* 排序控件 */}
                <div className="sort-controls">
                    <label>排序：</label>
                    <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                        <option value="combined">综合得分</option>
                        <option value="semantic_score">语义相关度</option>
                        <option value="citation_count">引用数</option>
                        <option value="published_date">发表日期</option>
                    </select>
                </div>
            </div>

            {/* 操作栏 */}
            {activeRuleset && (
                <div className="actions-bar">
                    <span className="paper-count">
                        🏆 精选 {curatedPapers.length} | 🆕 新增 {newPapers.length}
                    </span>
                    {fetchStatus && (
                        <span className="fetch-status">{fetchStatus}</span>
                    )}
                    <div className="action-buttons">
                        {!isCollected ? (
                            <button
                                className="action-btn fetch-btn"
                                onClick={() => handleTriggerCollect(activeRulesetId)}
                                disabled={!!fetchStatus}
                            >
                                📚 开始收集历史精选
                            </button>
                        ) : (
                            <button
                                className="action-btn fetch-btn"
                                onClick={() => handleTriggerTrack(activeRulesetId)}
                                disabled={!!fetchStatus}
                            >
                                🔄 追踪新论文
                            </button>
                        )}
                        <button
                            className="action-btn score-btn"
                            onClick={() => handleTriggerScore(activeRulesetId)}
                            disabled={!!fetchStatus}
                        >
                            ⭐ LLM评分
                        </button>
                        <button
                            className="action-btn edit-btn"
                            onClick={() => navigate(`/rulesets/${activeRulesetId}/edit`)}
                        >
                            ✏️ 编辑规则
                        </button>
                    </div>
                </div>
            )}

            {/* 论文列表 - 分区显示 */}
            <div className="papers-list">
                {loading ? (
                    <div className="loading">加载中...</div>
                ) : papers.length === 0 ? (
                    <div className="empty-state">
                        <p>暂无论文</p>
                        <p>点击"开始收集历史精选"开始</p>
                    </div>
                ) : (
                    <>
                        {/* 新论文区 */}
                        {newPapers.length > 0 && (
                            <div className="paper-section new-section">
                                <h3 className="section-title">🆕 本周新增 ({newPapers.length}篇)</h3>
                                {newPapers.map(paper => renderPaperCard(paper))}
                            </div>
                        )}

                        {/* 精选历史区 */}
                        {curatedPapers.length > 0 && (
                            <div className="paper-section curated-section">
                                <h3 className="section-title">🏆 精选历史 ({curatedPapers.length}篇)</h3>
                                {curatedPapers.map(paper => renderPaperCard(paper))}
                            </div>
                        )}

                        {/* 如果没有分区数据，显示全部 */}
                        {newPapers.length === 0 && curatedPapers.length === 0 && (
                            papers.map(paper => renderPaperCard(paper))
                        )}
                    </>
                )}
            </div>
        </div>
    )

    // 渲染论文卡片
    function renderPaperCard(paper) {
        return (
            <div key={paper.id} className={`paper-card ${paper.is_curated ? 'curated' : ''}`}>
                <div className="paper-header">
                    <h3
                        className="paper-title clickable"
                        onClick={() => onPaperSelect && onPaperSelect(paper)}
                    >
                        {paper.is_curated && <span className="badge curated">🏆</span>}
                        {paper.is_new && <span className="badge new">🆕</span>}
                        {paper.title}
                    </h3>
                    <div className="paper-scores">
                        {paper.semantic_score && (
                            <span className="score semantic" title="语义相关度">
                                🎯 {paper.semantic_score.toFixed(1)}
                            </span>
                        )}
                        <span className="score citation" title="引用数">
                            📚 {paper.citation_count || 0}
                        </span>
                        {paper.venue && (
                            <span className="score venue" title="发表">
                                📰 {paper.venue}
                            </span>
                        )}
                    </div>
                </div>
                <div className="paper-meta">
                    <span className="authors">
                        {paper.authors?.slice(0, 3).join(', ')}
                        {paper.authors?.length > 3 && ' 等'}
                    </span>
                    <span className="date">
                        {paper.published_date?.split('T')[0]}
                    </span>
                </div>
                <div className="paper-categories">
                    {paper.categories?.map(cat => (
                        <span key={cat} className="category-tag">{cat}</span>
                    ))}
                </div>
                {paper.score_reason && (
                    <div className="score-reason">{paper.score_reason}</div>
                )}
                {/* 用户反馈按钮 */}
                <div className="paper-actions">
                    <button
                        className={`action-icon ${paper.is_starred ? 'active' : ''}`}
                        title="收藏"
                        onClick={(e) => { e.stopPropagation(); handleToggleStar(paper) }}
                    >
                        {paper.is_starred ? '⭐' : '☆'}
                    </button>
                    <button
                        className={`action-icon ${paper.feedback === 'valuable' ? 'active-good' : ''}`}
                        title="有价值"
                        onClick={(e) => { e.stopPropagation(); handleFeedback(paper, 'valuable') }}
                    >
                        👍
                    </button>
                    <button
                        className={`action-icon ${paper.feedback === 'not_valuable' ? 'active-bad' : ''}`}
                        title="无价值"
                        onClick={(e) => { e.stopPropagation(); handleFeedback(paper, 'not_valuable') }}
                    >
                        👎
                    </button>
                </div>
            </div>
        )
    }
}
