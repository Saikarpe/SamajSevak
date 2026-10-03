import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { BarChart3, BrainCircuit, FolderHeart, LayoutDashboard, ListChecks, Lock, LogOut, MapPinned, MessageSquarePlus, Scale, SearchCheck, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, scopeLabel, session } from './api'
import Dashboard from './pages/Dashboard'
import Submit from './pages/Submit'
import Track from './pages/Track'
import MyComplaints from './pages/MyComplaints'
import PublicStats from './pages/PublicStats'
import Queue from './pages/Queue'
import Detail from './pages/Detail'
import Insights from './pages/Insights'
import AILab from './pages/AILab'
import Login from './pages/Login'

export default function App() {
  const [meta, setMeta] = useState(null)
  const [officer, setOfficer] = useState(session.get)
  const location = useLocation()
  useEffect(() => { api.meta().then(setMeta).catch(() => {}) }, [])
  useEffect(() => {
    const sync = () => setOfficer(session.get())
    window.addEventListener('officer', sync); window.addEventListener('storage', sync)
    return () => { window.removeEventListener('officer', sync); window.removeEventListener('storage', sync) }
  }, [])
  const link = (to, Icon, label, locked) => (
    <NavLink to={to} end={to === '/'}><Icon size={18} />{label}{locked && <Lock size={12} style={{ marginLeft: 'auto', opacity: .6 }} />}</NavLink>
  )
  // officer pages redirect to the login form and come back afterwards
  const guard = (page) => (officer ? page : <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />)
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
          {link('/my', FolderHeart, 'My Complaints')}
          {link('/public', Scale, 'Public Accountability')}
          <div className="nav-label">Officer Console</div>
          {link('/', LayoutDashboard, 'Command Center', !officer)}
          {link('/grievances', ListChecks, 'Priority Queue', !officer)}
          {link('/insights', MapPinned, 'Hotspots & Insights', !officer)}
          {link('/ai-lab', BrainCircuit, 'AI Engine', !officer)}
        </nav>
        <div className="sidebar-foot">
          {officer && (
            <div style={{ marginBottom: 8 }}>
              <div className="row-flex between">
                <span>{officer.name}</span>
                <button className="link" onClick={() => session.set(null)} title="Sign out"><LogOut size={14} /> Sign out</button>
              </div>
              <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{scopeLabel(officer)}</div>
            </div>
          )}
          <div><span className="dot" />AI engine online</div>
          <div className="muted" style={{ marginTop: 4 }}>
            <BarChart3 size={12} style={{ verticalAlign: -2 }} /> LLM: {meta?.llm_provider || 'offline mode (templates)'}
          </div>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/login" element={officer ? <Navigate to={location.state?.from || '/'} replace /> : <Login meta={meta} />} />
          <Route path="/citizen" element={<Submit meta={meta} />} />
          <Route path="/track" element={<Track />} />
          <Route path="/track/:id" element={<Track />} />
          <Route path="/my" element={<MyComplaints />} />
          <Route path="/public" element={<PublicStats />} />
          <Route path="/" element={guard(<Dashboard />)} />
          <Route path="/grievances" element={guard(<Queue meta={meta} />)} />
          <Route path="/grievances/:id" element={guard(<Detail meta={meta} />)} />
          <Route path="/insights" element={guard(<Insights />)} />
          <Route path="/ai-lab" element={guard(<AILab meta={meta} />)} />
        </Routes>
      </main>
    </div>
  )
}
