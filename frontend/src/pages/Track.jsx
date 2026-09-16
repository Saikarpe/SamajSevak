import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api, fmtHours, STATUS_COLORS } from '../api'
import { Card, PriorityBadge, StatusBadge } from '../components/ui'

const FLOW = ['Submitted', 'Assigned', 'In Progress', 'Resolved']

export default function Track() {
  const { id } = useParams()
  const nav = useNavigate()
  const [q, setQ] = useState(id || '')
  const [g, setG] = useState(null)
  const [err, setErr] = useState('')
  const [rated, setRated] = useState(0)

  useEffect(() => {
    if (!id) return
    setErr(''); setG(null)
    api.get(id).then((d) => { setG(d); setRated(d.feedback_rating || 0) }).catch(() => setErr('No grievance found with this ID.'))
  }, [id])

  const stage = g ? FLOW.indexOf(g.status) : -1
  const rate = async (n) => { setRated(n); setG(await api.feedback(g.id, n)) }

  return (
    <div style={{ maxWidth: 820, margin: '0 auto' }}>
      <div className="page-head"><div><h2>Track your grievance</h2><p>Enter the tracking ID you received (e.g. SS-2026-00454).</p></div></div>
      <Card>
        <form className="row-flex" onSubmit={(e) => { e.preventDefault(); nav(`/track/${q.trim()}`) }}>
          <input className="input" style={{ flex: 1 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="SS-2026-00001" />
          <button className="btn primary"><Search size={16} /> Track</button>
        </form>
        {err && <p style={{ color: '#dc2626' }}>{err}</p>}
      </Card>
      {g && (
        <div className="grid" style={{ marginTop: 16 }}>
          <Card title={<span className="mono">{g.id}</span>} right={<StatusBadge status={g.status} />}>
            <p style={{ marginTop: 0 }}>{g.text}</p>
            <div className="row-flex small muted"><PriorityBadge level={g.priority_level} /> {g.department} · {g.ward} · SLA {fmtHours(g.analysis?.recommendation?.sla_hours)}</div>
            <div className="row-flex" style={{ marginTop: 22, gap: 0, flexWrap: 'nowrap' }}>
              {FLOW.map((s, i) => (
                <div key={s} style={{ flex: 1, textAlign: 'center' }}>
                  <div style={{ height: 6, background: i <= stage ? STATUS_COLORS[g.status] : '#e5e9f2', borderRadius: 4, margin: '0 3px' }} />
                  <div className="small" style={{ marginTop: 6, fontWeight: i === stage ? 700 : 400, color: i <= stage ? '#0f172a' : '#94a3b8' }}>{s}</div>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Updates">
            <ul className="timeline">
              {g.timeline.map((t, i) => (
                <li key={i} style={{ '--c': STATUS_COLORS[t.status] || '#f59e0b' }}>
                  <b className="small">{t.status}</b> <span className="small muted">· {new Date(t.ts).toLocaleString()} · {t.actor}</span>
                  <div style={{ fontSize: 14 }}>{t.note}</div>
                </li>
              ))}
            </ul>
          </Card>
          {g.status === 'Resolved' && (
            <Card title="Rate the resolution">
              <div className="stars">{[1, 2, 3, 4, 5].map((n) => <button key={n} className={n <= rated ? 'on' : ''} onClick={() => rate(n)}>★</button>)}</div>
              <p className="small muted">Your rating trains department performance scores.</p>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
