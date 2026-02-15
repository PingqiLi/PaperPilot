import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Star, Trash2 } from 'lucide-react'
import { updatePaper } from '../api/papers'
import './Favorites.css'

/**
 * 收藏夹页面 - 显示用户收藏的论文
 */
export default function Favorites() {
    const navigate = useNavigate()
    const [papers, setPapers] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadFavorites()
    }, [])

    const loadFavorites = async () => {
        try {
            const response = await fetch('/api/v1/papers?feedback=good&page_size=100')
            const data = await response.json()
            setPapers(data.items || [])
        } catch (err) {
            console.error('加载收藏失败:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleRemoveFavorite = async (paper) => {
        try {
            await updatePaper(paper.id, { feedback: null })
            setPapers(prev => prev.filter(p => p.id !== paper.id))
        } catch (err) {
            console.error('移除收藏失败:', err)
        }
    }

    if (loading) {
        return (
            <div className="favorites-page">
                <div className="loading">加载中...</div>
            </div>
        )
    }

    return (
        <div className="favorites-page fade-in">
            <header className="page-header">
                <h1 className="page-title">⭐ 收藏夹</h1>
                <p className="page-subtitle">你标记为"好文"的论文 ({papers.length}篇)</p>
            </header>

            {papers.length === 0 ? (
                <div className="empty-state">
                    <Star size={48} />
                    <p>暂无收藏</p>
                    <p className="hint">在论文列表中点击👍按钮收藏论文</p>
                </div>
            ) : (
                <div className="favorites-list">
                    {papers.map(paper => (
                        <div key={paper.id} className="favorite-card">
                            <div className="favorite-content" onClick={() => navigate(`/papers/${paper.id}`)}>
                                <h3 className="favorite-title">{paper.title}</h3>
                                <div className="favorite-meta">
                                    <span className="authors">{paper.authors?.slice(0, 3).join(', ')}</span>
                                    <span className="date">{paper.published_date?.split('T')[0]}</span>
                                    {paper.citation_count > 0 && (
                                        <span className="citations">📊 {paper.citation_count}引用</span>
                                    )}
                                </div>
                            </div>
                            <button
                                className="remove-btn"
                                onClick={() => handleRemoveFavorite(paper)}
                                title="移除收藏"
                            >
                                <Trash2 size={18} />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
