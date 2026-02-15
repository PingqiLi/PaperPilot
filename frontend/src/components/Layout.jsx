import { Link, useLocation } from 'react-router-dom'
import { FileText, Settings, Star, Search } from 'lucide-react'
import './Layout.css'

function Layout({ children }) {
    const location = useLocation()

    return (
        <div className="layout">
            {/* 侧边栏 */}
            <aside className="sidebar">
                <div className="sidebar-header">
                    <div className="logo">
                        <div className="logo-icon">📚</div>
                        <span className="logo-text">Paper Agent</span>
                    </div>
                </div>

                <nav className="nav">
                    <Link
                        to="/"
                        className={`nav-item ${location.pathname === '/' ? 'active' : ''}`}
                    >
                        <FileText size={20} />
                        <span>论文订阅</span>
                    </Link>
                    <Link
                        to="/favorites"
                        className={`nav-item ${location.pathname === '/favorites' ? 'active' : ''}`}
                    >
                        <Star size={20} />
                        <span>收藏夹</span>
                    </Link>
                    <Link
                        to="/search"
                        className={`nav-item ${location.pathname === '/search' ? 'active' : ''}`}
                    >
                        <Search size={20} />
                        <span>搜索论文</span>
                    </Link>
                    <div className="nav-divider" />
                    <Link
                        to="/rules"
                        className={`nav-item ${location.pathname === '/rules' ? 'active' : ''}`}
                    >
                        <Settings size={20} />
                        <span>全局设置</span>
                    </Link>
                </nav>

                <div className="sidebar-footer">
                    <div className="footer-stats">
                        <span className="stat-text">ArXiv论文助手</span>
                    </div>
                </div>
            </aside>

            {/* 主内容区 */}
            <main className="main-content">
                {children}
            </main>
        </div>
    )
}

export default Layout
