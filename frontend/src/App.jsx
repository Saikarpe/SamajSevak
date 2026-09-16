import { NavLink, Route, Routes } from 'react-router-dom'
import { BarChart3, BrainCircuit, LayoutDashboard, ListChecks, MapPinned, MessageSquarePlus, SearchCheck, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from './api'
import Dashboard from './pages/Dashboard'
import Submit from './pages/Submit'
import Track from './pages/Track'
import Queue from './pages/Queue'
import Detail from './pages/Detail'
import Insights from './pages/Insights'
import AILab from './pages/AILab'

export default function App() {
  const [meta, setMeta] = useState(null)
  useEffect(() => { api.meta().then(setMeta).catch(() => {}) }, [])
  const link = (to, Icon, label) => (
    <NavLink to={to} end={to === '/'}><Icon size={18} />{label}</NavLink>
  )
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo"><ShieldCheck size={22} /></div>
          <div><h1>SamajSevak</h1><small>AI Grievance Intelligence</small></div>
        </div>
        <nav className="nav">
          <div className="nav-label">Citizen</div>
          {link('/citizen', MessageSquarePlus, 'Raise Grievance')}
          {link('/track', SearchCheck, 'Track Status')}
          <div className="nav-label">Officer Console</div>
          {link('/', LayoutDashboard, 'Command Center')}
          {link('/grievances', ListChecks, 'Priority Queue')}
          {link('/insights', MapPinned, 'Hotspots & Insights')}
          {link('/ai-lab', BrainCircuit, 'AI Engine')}
        </nav>
        <div className="sidebar-foot">
          <div><span className="dot" />AI engine online</div>
          <div className="muted" style={{ marginTop: 4 }}>
            <BarChart3 size={12} style={{ verticalAlign: -2 }} /> LLM: {meta?.llm_provider || 'offline mode (templates)'}
          </div>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/citizen" element={<Submit meta={meta} />} />
          <Route path="/track" element={<Track />} />
          <Route path="/track/:id" element={<Track />} />
          <Route path="/grievances" element={<Queue meta={meta} />} />
          <Route path="/grievances/:id" element={<Detail meta={meta} />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/ai-lab" element={<AILab meta={meta} />} />
        </Routes>
      </main>
    </div>
  )
}
