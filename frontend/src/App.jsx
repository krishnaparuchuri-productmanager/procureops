import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar.jsx'
import HomePage from './pages/HomePage.jsx'
import DecisionsQueuePage from './pages/DecisionsQueuePage.jsx'
import DecisionDetailPage from './pages/DecisionDetailPage.jsx'
import NewRequestPage from './pages/NewRequestPage.jsx'
import VendorsPage from './pages/VendorsPage.jsx'
import PolicyPage from './pages/PolicyPage.jsx'
import AuditLogPage from './pages/AuditLogPage.jsx'
import AgentActivityPage from './pages/AgentActivityPage.jsx'
import NegotiationBriefPage from './pages/NegotiationBriefPage.jsx'
import AutonomyPolicyPage from './pages/AutonomyPolicyPage.jsx'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/decisions" element={<DecisionsQueuePage />} />
          <Route path="/decisions/:id" element={<DecisionDetailPage />} />
          <Route path="/new" element={<NewRequestPage />} />
          <Route path="/vendors" element={<VendorsPage />} />
          <Route path="/policy" element={<PolicyPage />} />
          <Route path="/audit" element={<AuditLogPage />} />
          <Route path="/activity" element={<AgentActivityPage />} />
          <Route path="/negotiation" element={<NegotiationBriefPage />} />
          <Route path="/autonomy-policy" element={<AutonomyPolicyPage />} />
        </Routes>
      </main>
      <footer className="border-t border-rule">
        <div className="max-w-6xl mx-auto px-6 py-4 font-mono text-[10px] uppercase tracking-wider text-ink-muted flex items-center justify-between">
          <span>ProcureOps — synthetic procurement governance demo. No real ERP or payment integration.</span>
          <span>Built by Krishna Paruchuri</span>
        </div>
      </footer>
    </div>
  )
}
