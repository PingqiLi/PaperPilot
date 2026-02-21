import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import RuleSetWizard from './pages/RuleSetWizard'
import RuleSetDashboard from './pages/RuleSetDashboard'
import PaperDetail from './pages/PaperDetail'
import CostStats from './pages/CostStats'
import AppSettings from './pages/AppSettings'

function App() {
    return (
        <Layout>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/topics/new" element={<RuleSetWizard />} />
                <Route path="/topics/:id" element={<RuleSetDashboard />} />
                <Route path="/topics/:id/papers/:paperId" element={<PaperDetail />} />
                <Route path="/stats" element={<CostStats />} />
                <Route path="/settings" element={<AppSettings />} />
            </Routes>
        </Layout>
    )
}

export default App
