import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import RuleSetHome from './pages/RuleSetHome'
import RuleSetEditor from './pages/RuleSetEditor'
import PaperList from './pages/PaperList'
import PaperDetail from './pages/PaperDetail'
import RulesConfig from './pages/RulesConfig'
import Favorites from './pages/Favorites'
import SearchPage from './pages/SearchPage'
import './App.css'

function App() {
    return (
        <Layout>
            <Routes>
                <Route path="/" element={<RuleSetHome />} />
                <Route path="/rulesets/new" element={<RuleSetEditor />} />
                <Route path="/rulesets/:id/edit" element={<RuleSetEditor />} />
                <Route path="/papers" element={<PaperList />} />
                <Route path="/papers/:id" element={<PaperDetail />} />
                <Route path="/rules" element={<RulesConfig />} />
                <Route path="/favorites" element={<Favorites />} />
                <Route path="/search" element={<SearchPage />} />
            </Routes>
        </Layout>
    )
}

export default App
