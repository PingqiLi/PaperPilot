import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Star, ExternalLink, RefreshCw, BookOpen, BarChart2, FileText, MessageSquare } from 'lucide-react'
import { fetchPaper, updatePaper, processPaper } from '../api/papers'
import { format } from 'date-fns'
import './PaperDetail.css'

function PaperDetail() {
    const { id } = useParams()
    const queryClient = useQueryClient()
    const [activeTab, setActiveTab] = useState('summary')

    const { data: paper, isLoading, error } = useQuery({
        queryKey: ['paper', id],
        queryFn: () => fetchPaper(id),
    })

    const updateMutation = useMutation({
        mutationFn: (updates) => updatePaper(id, updates),
        onSuccess: () => {
            queryClient.invalidateQueries(['paper', id])
        }
    })

    const processMutation = useMutation({
        mutationFn: () => processPaper(id),
        onSuccess: () => {
            queryClient.invalidateQueries(['paper', id])
        }
    })

    const getScoreClass = (score) => {
        if (!score) return ''
        if (score >= 7) return 'score-high'
        if (score >= 4) return 'score-medium'
        return 'score-low'
    }

    if (isLoading) {
        return (
            <div className="loading-state">
                <div className="loading-spinner"></div>
                <p>加载中...</p>
            </div>
        )
    }

    if (error || !paper) {
        return (
            <div className="error-state">
                <p>论文不存在或加载失败</p>
                <Link to="/" className="btn btn-primary">返回列表</Link>
            </div>
        )
    }

    return (
        <div className="paper-detail-page fade-in">
            {/* 顶部导航 */}
            <div className="detail-nav">
                <Link to="/" className="btn btn-ghost">
                    <ArrowLeft size={18} />
                    返回列表
                </Link>
                <div className="detail-actions">
                    <button
                        className="btn btn-secondary"
                        onClick={() => updateMutation.mutate({ is_starred: !paper.is_starred })}
                    >
                        <Star
                            size={18}
                            fill={paper.is_starred ? '#f59e0b' : 'none'}
                            color={paper.is_starred ? '#f59e0b' : 'currentColor'}
                        />
                        {paper.is_starred ? '已收藏' : '收藏'}
                    </button>
                    {!paper.is_processed && (
                        <button
                            className="btn btn-primary"
                            onClick={() => processMutation.mutate()}
                            disabled={processMutation.isPending}
                        >
                            <RefreshCw size={18} className={processMutation.isPending ? 'spin' : ''} />
                            {processMutation.isPending ? '处理中...' : '生成摘要'}
                        </button>
                    )}
                    {paper.pdf_url && (
                        <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
                            <ExternalLink size={18} />
                            查看PDF
                        </a>
                    )}
                </div>
            </div>

            {/* 论文标题和元信息 */}
            <header className="detail-header">
                <div className="detail-score-section">
                    <div className={`score-indicator large ${getScoreClass(paper.relevance_score)}`}>
                        {paper.relevance_score || '-'}
                    </div>
                    {paper.score_reason && (
                        <p className="score-reason">{paper.score_reason}</p>
                    )}
                </div>

                <h1 className="detail-title">{paper.title}</h1>

                <div className="detail-meta">
                    <p className="detail-authors">
                        <strong>作者:</strong> {paper.authors?.join(', ')}
                    </p>
                    <p className="detail-date">
                        <strong>发布日期:</strong> {paper.published_date && format(new Date(paper.published_date), 'yyyy年MM月dd日')}
                    </p>
                    <div className="detail-categories">
                        {paper.categories?.map((cat) => (
                            <span key={cat} className="badge badge-primary">{cat}</span>
                        ))}
                    </div>
                </div>
            </header>

            {/* 标签页导航 */}
            <div className="detail-tabs">
                <button
                    className={`tab-button ${activeTab === 'summary' ? 'active' : ''}`}
                    onClick={() => setActiveTab('summary')}
                >
                    <FileText size={16} />
                    摘要 & 关键点
                </button>
                <button
                    className={`tab-button ${activeTab === 'analysis' ? 'active' : ''}`}
                    onClick={() => setActiveTab('analysis')}
                    disabled={!paper.analysis && !paper.figures}
                    title={!paper.analysis ? "暂无图表分析数据" : ""}
                >
                    <BarChart2 size={16} />
                    图表分析
                    {(!paper.analysis && !paper.figures) && <span className="tab-badge">无</span>}
                </button>
                <button
                    className={`tab-button ${activeTab === 'notes' ? 'active' : ''}`}
                    onClick={() => setActiveTab('notes')}
                >
                    <MessageSquare size={16} />
                    笔记
                </button>
            </div>

            {/* 内容区域 */}
            <div className="detail-content">

                {/* 摘要 & 关键点 */}
                {activeTab === 'summary' && (
                    <div className="tab-content fade-in">
                        {/* 原始摘要 */}
                        <section className="content-section">
                            <h2 className="section-title">
                                <BookOpen size={20} />
                                原始摘要
                            </h2>
                            <p className="abstract-text">{paper.abstract}</p>
                        </section>

                        {/* AI生成摘要 */}
                        {paper.summary && (
                            <section className="content-section highlight">
                                <h2 className="section-title">AI 摘要</h2>
                                <p>{paper.summary}</p>
                            </section>
                        )}

                        {/* 关键发现 */}
                        {paper.key_findings?.length > 0 && (
                            <section className="content-section">
                                <h2 className="section-title">关键发现</h2>
                                <ul className="key-findings-list">
                                    {paper.key_findings.map((finding, index) => (
                                        <li key={index}>{finding}</li>
                                    ))}
                                </ul>
                            </section>
                        )}

                        {/* 方法论 */}
                        {paper.methodology && (
                            <section className="content-section">
                                <h2 className="section-title">技术方法</h2>
                                <p>{paper.methodology}</p>
                            </section>
                        )}

                        {/* 抽取的信息 */}
                        {paper.extracted_info && Object.keys(paper.extracted_info).length > 0 && (
                            <section className="content-section">
                                <h2 className="section-title">抽取信息</h2>
                                <div className="extracted-info-grid">
                                    {paper.extracted_info.keywords?.length > 0 && (
                                        <div className="info-item">
                                            <h4>关键词</h4>
                                            <div className="tag-list">
                                                {paper.extracted_info.keywords.map((kw, i) => (
                                                    <span key={i} className="badge">{kw}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {paper.extracted_info.datasets?.length > 0 && (
                                        <div className="info-item">
                                            <h4>数据集</h4>
                                            <div className="tag-list">
                                                {paper.extracted_info.datasets.map((ds, i) => (
                                                    <span key={i} className="badge badge-success">{ds}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {paper.extracted_info.code_url && (
                                        <div className="info-item">
                                            <h4>代码</h4>
                                            <a href={paper.extracted_info.code_url} target="_blank" rel="noopener noreferrer">
                                                {paper.extracted_info.code_url}
                                            </a>
                                        </div>
                                    )}
                                </div>
                            </section>
                        )}
                    </div>
                )}

                {/* 图表分析 */}
                {activeTab === 'analysis' && (
                    <div className="tab-content fade-in">
                        {paper.analysis ? (
                            <div className="analysis-grid">
                                {paper.analysis.map((item, index) => (
                                    <div key={index} className="analysis-card">
                                        <h3>图表 {index + 1}</h3>
                                        {item.image_path && (
                                            <img src={item.image_path} alt={`Figure ${index + 1}`} className="analysis-image" />
                                        )}
                                        <div className="analysis-text">
                                            <p><strong>描述:</strong> {item.description}</p>
                                            <p><strong>分析:</strong> {item.analysis}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="empty-state">
                                <p>暂无图表分析数据</p>
                            </div>
                        )}
                    </div>
                )}

                {/* 笔记 */}
                {activeTab === 'notes' && (
                    <div className="tab-content fade-in">
                        <section className="content-section">
                            <h2 className="section-title">我的笔记</h2>
                            <textarea
                                className="input notes-input"
                                placeholder="在这里记录你的想法..."
                                value={paper.user_notes || ''}
                                onChange={(e) => updateMutation.mutate({ user_notes: e.target.value })}
                                rows={8}
                            />
                        </section>
                    </div>
                )}

            </div>
        </div>
    )
}

export default PaperDetail
