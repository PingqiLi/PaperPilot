import { useNavigate } from 'react-router-dom'
import RuleSetTabs from '../components/RuleSetTabs'
import './RuleSetHome.css'

/**
 * 规则集主页 - 支持多规则集Tab切换
 */
export default function RuleSetHome() {
    const navigate = useNavigate()

    const handlePaperSelect = (paper) => {
        navigate(`/papers/${paper.id}`)
    }

    return (
        <div className="ruleset-home">
            <header className="page-header">
                <h1 className="page-title">📚 论文订阅</h1>
                <p className="page-subtitle">按规则集浏览和管理论文</p>
            </header>

            <RuleSetTabs onPaperSelect={handlePaperSelect} />
        </div>
    )
}
