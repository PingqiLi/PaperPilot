import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import './SearchPage.css'

/**
 * 搜索页面 - 搜索已收集的论文
 */
export default function SearchPage() {
    const navigate = useNavigate()
    const [query, setQuery] = useState('')
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [searched, setSearched] = useState(false)

    const handleSearch = async () => {
        if (!query.trim()) return

        setLoading(true)
        setSearched(true)
        try {
            const response = await fetch(`/api/v1/papers?search=${encodeURIComponent(query)}&page_size=50`)
            const data = await response.json()
            setResults(data.items || [])
        } catch (err) {
            console.error('搜索失败:', err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="search-page fade-in">
            <header className="page-header">
                <h1 className="page-title">🔍 搜索论文</h1>
                <p className="page-subtitle">在已收集的论文中搜索</p>
            </header>

            <div className="search-box">
                <input
                    type="text"
                    className="search-input"
                    placeholder="输入关键词搜索..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                />
                <button
                    className="search-btn"
                    onClick={handleSearch}
                    disabled={loading}
                >
                    <Search size={20} />
                    {loading ? '搜索中...' : '搜索'}
                </button>
            </div>

            {searched && !loading && (
                <div className="search-results">
                    <p className="results-count">
                        找到 {results.length} 篇相关论文
                    </p>

                    {results.length === 0 ? (
                        <div className="no-results">
                            <p>未找到匹配的论文</p>
                            <p className="hint">尝试使用不同的关键词</p>
                        </div>
                    ) : (
                        <div className="results-list">
                            {results.map(paper => (
                                <div
                                    key={paper.id}
                                    className="result-card"
                                    onClick={() => navigate(`/papers/${paper.id}`)}
                                >
                                    <h3 className="result-title">{paper.title}</h3>
                                    <div className="result-meta">
                                        <span className="authors">{paper.authors?.slice(0, 3).join(', ')}</span>
                                        <span className="date">{paper.published_date?.split('T')[0]}</span>
                                        {paper.citation_count > 0 && (
                                            <span className="citations">📊 {paper.citation_count}引用</span>
                                        )}
                                    </div>
                                    {paper.abstract && (
                                        <p className="result-abstract">
                                            {paper.abstract.slice(0, 200)}...
                                        </p>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
