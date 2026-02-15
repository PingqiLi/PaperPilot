import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Star, ExternalLink, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react'
import { fetchPapers, updatePaper } from '../api/papers'
import { format } from 'date-fns'
import './PaperList.css'

function PaperList() {
    const queryClient = useQueryClient()
    const [page, setPage] = useState(1)
    const [search, setSearch] = useState('')
    const [filters, setFilters] = useState({
        minScore: null,
        starredOnly: false,
        unreadOnly: false,
        category: '',
    })

    const { data, isLoading, error } = useQuery({
        queryKey: ['papers', page, search, filters],
        queryFn: () => fetchPapers({
            page,
            page_size: 20,
            search: search || undefined,
            min_score: filters.minScore || undefined,
            starred_only: filters.starredOnly || undefined,
            unread_only: filters.unreadOnly || undefined,
            category: filters.category || undefined,
        }),
    })

    const starMutation = useMutation({
        mutationFn: ({ id, isStarred }) => updatePaper(id, { is_starred: isStarred }),
        onSuccess: () => {
            queryClient.invalidateQueries(['papers'])
        }
    })

    const getScoreClass = (score) => {
        if (!score) return ''
        if (score >= 7) return 'score-high'
        if (score >= 4) return 'score-medium'
        return 'score-low'
    }

    if (error) {
        return (
            <div className="error-state">
                <p>加载失败: {error.message}</p>
                <button className="btn btn-primary" onClick={() => queryClient.invalidateQueries(['papers'])}>
                    重试
                </button>
            </div>
        )
    }

    return (
        <div className="paper-list-page">
            {/* 页面头部 */}
            <header className="page-header">
                <h1 className="page-title">论文列表</h1>
                <p className="page-subtitle">
                    共 {data?.total || 0} 篇论文
                </p>
            </header>

            {/* 搜索和筛选 */}
            <div className="toolbar">
                <div className="search-box">
                    <Search size={18} className="search-icon" />
                    <input
                        type="text"
                        className="input search-input"
                        placeholder="搜索论文标题或摘要..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>

                <div className="filters">
                    <select
                        className="input filter-select"
                        value={filters.minScore || ''}
                        onChange={(e) => setFilters({ ...filters, minScore: e.target.value ? Number(e.target.value) : null })}
                    >
                        <option value="">全部评分</option>
                        <option value="7">≥7分 (高相关)</option>
                        <option value="5">≥5分 (中等)</option>
                    </select>

                    <button
                        className={`btn ${filters.starredOnly ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setFilters({ ...filters, starredOnly: !filters.starredOnly })}
                    >
                        <Star size={16} fill={filters.starredOnly ? 'currentColor' : 'none'} />
                        收藏
                    </button>

                    <button
                        className={`btn ${filters.unreadOnly ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setFilters({ ...filters, unreadOnly: !filters.unreadOnly })}
                    >
                        未读
                    </button>
                </div>
            </div>

            {/* 论文列表 */}
            {isLoading ? (
                <div className="loading-state">
                    <div className="loading-spinner"></div>
                    <p>加载中...</p>
                </div>
            ) : (
                <>
                    <div className="paper-grid">
                        {data?.items?.map((paper) => (
                            <article key={paper.id} className="paper-card card fade-in">
                                <div className="paper-card-header">
                                    <div className="paper-score">
                                        {paper.relevance_score ? (
                                            <div className={`score-indicator ${getScoreClass(paper.relevance_score)}`}>
                                                {paper.relevance_score}
                                            </div>
                                        ) : (
                                            <div className="score-indicator">-</div>
                                        )}
                                    </div>
                                    <div className="paper-actions">
                                        <button
                                            className="btn btn-ghost"
                                            onClick={() => starMutation.mutate({
                                                id: paper.id,
                                                isStarred: !paper.is_starred
                                            })}
                                        >
                                            <Star
                                                size={18}
                                                fill={paper.is_starred ? '#f59e0b' : 'none'}
                                                color={paper.is_starred ? '#f59e0b' : 'currentColor'}
                                            />
                                        </button>
                                    </div>
                                </div>

                                <Link to={`/papers/${paper.id}`} className="paper-card-content">
                                    <h3 className="paper-title">{paper.title}</h3>
                                    <p className="paper-authors">
                                        {paper.authors?.slice(0, 3).join(', ')}
                                        {paper.authors?.length > 3 && ' 等'}
                                    </p>
                                </Link>

                                <div className="paper-card-footer">
                                    <div className="paper-categories">
                                        {paper.categories?.slice(0, 2).map((cat) => (
                                            <span key={cat} className="badge badge-primary">{cat}</span>
                                        ))}
                                    </div>
                                    <span className="paper-date">
                                        {paper.published_date && format(new Date(paper.published_date), 'yyyy-MM-dd')}
                                    </span>
                                </div>
                            </article>
                        ))}
                    </div>

                    {/* 分页 */}
                    {data && data.total > 20 && (
                        <div className="pagination">
                            <button
                                className="btn btn-secondary"
                                disabled={page === 1}
                                onClick={() => setPage(p => p - 1)}
                            >
                                <ChevronLeft size={18} />
                                上一页
                            </button>
                            <span className="page-info">
                                第 {page} 页 / 共 {Math.ceil(data.total / 20)} 页
                            </span>
                            <button
                                className="btn btn-secondary"
                                disabled={page * 20 >= data.total}
                                onClick={() => setPage(p => p + 1)}
                            >
                                下一页
                                <ChevronRight size={18} />
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

export default PaperList
