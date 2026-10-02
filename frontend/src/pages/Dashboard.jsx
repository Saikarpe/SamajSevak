import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Area, AreaChart, Bar as RBar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlarmClock, CheckCircle2, Flame, Inbox, Layers, Siren, Star, Timer, TrendingUp } from 'lucide-react'
import { api, fmtHours, PRIORITY_COLORS, STAGE_COLORS, timeAgo } from '../api'
import { Card, PriorityBadge, StageBadge, Stat, StatusBadge } from '../components/ui'

export default function Dashboard() {
  const [s, setS] = useState(null)
  const [an, setAn] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [queue, setQueue] = useState([])
  const nav = useNavigate()
  useEffect(() => {
    api.stats().then(setS); api.analytics().then(setAn); api.alerts().then(setAlerts)
    api.list({ limit: 8 }).then(setQueue)
  }, [])
  if (!s || !an) return <div className="empty pulse">Loading command center…</div>
  return (
    <>
      <div className="page-head">
        <div><h2>Command Center</h2><p>Real-time view of citizen grievances, AI-prioritised for action.</p></div>
        <Link className="btn saffron" to="/citizen">+ New grievance</Link>
      </div>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <Stat icon={Inbox} label="Open issues" value={s.open_issues} hint={`${s.total} citizen reports · ${s.last_7_days} in last 7 days`} />
        <Stat icon={Siren} label="Critical open" value={s.critical_open} color="#dc2626" hint="Highest AI priority score" />
        <Stat icon={AlarmClock} label="SLA breached / at risk" value={`${s.sla_breached_open} / ${s.sla_at_risk}`} color="#ea580c" hint="At risk = due in < 12 h" />
        <Stat icon={CheckCircle2} label="Confirmed by citizens" value={s.closed} color="#16a34a" hint={`${s.awaiting_confirmation} resolved, awaiting confirmation`} />
      </div>
      <Card title={<><Layers size={18} color="#2563eb" /> Accountability</>} sub="open issues by escalation stage · seeded demo data" style={{ marginBottom: 16 }}>
        <div className="stage-row">
          {Object.entries(s.stages).map(([stage, n]) => (
            <button key={stage} onClick={() => nav(`/grievances?stage=${encodeURIComponent(stage)}`)} style={{ borderTopColor: STAGE_COLORS[stage] }}>
              <b>{n}</b><span>{stage}</span>
            </button>
          ))}
          <button onClick={() => nav('/grievances?status=Not Satisfied')} style={{ borderTopColor: '#dc2626' }}><b>{s.not_satisfied}</b><span>Citizen not satisfied</span></button>
          <button onClick={() => nav('/grievances')} style={{ borderTopColor: '#2563eb' }}><b>{s.multi_report_issues}</b><span>Issues with several reports ({s.linked_reports} linked)</span></button>
          <button onClick={() => nav('/grievances?flagged=true')} style={{ borderTopColor: '#8a949e' }}><b>{s.abuse_review}</b><span>Reports flagged for review</span></button>
        </div>
        <p className="small muted" style={{ marginBottom: 0 }}>Complaint and Warning stay with the department. Strike 1 goes to its higher authority, Strike 2 to the Deputy Collector, Strike 3 to the final escalation body. {s.duplicate_candidates} open issue(s) have a possible duplicate for an officer to check; {s.rejected} rejected.</p>
      </Card>
      <div className="grid g-main" style={{ marginBottom: 16 }}>
        <Card title={<><TrendingUp size={18} /> Grievance inflow — last 30 days</>}>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={an.trend}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#2563eb" stopOpacity={.18} /><stop offset="100%" stopColor="#2563eb" stopOpacity={0} /></linearGradient>
                <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ea580c" stopOpacity={.18} /><stop offset="100%" stopColor="#ea580c" stopOpacity={0} /></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={4} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} width={28} />
              <Tooltip />
              <Area type="monotone" dataKey="received" name="Received" stroke="#2563eb" fill="url(#g1)" strokeWidth={2} />
              <Area type="monotone" dataKey="critical" name="High/Critical" stroke="#ea580c" fill="url(#g2)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
        <Card title={<><Flame size={18} color="#dc2626" /> AI Alerts</>} sub="Emerging issues & SLA risk">
          <div style={{ maxHeight: 250, overflowY: 'auto' }}>
            {alerts.length === 0 && <div className="muted small">No anomalies detected.</div>}
            {alerts.map((a, i) => (
              <div key={i} className={`alert ${a.severity}`}>
                <b>{a.message}</b>
                <p><b>Recommended:</b> {a.recommendation}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className="grid g-main" style={{ marginBottom: 16 }}>
        <Card title="Top of the AI priority queue" right={<Link className="small" style={{ color: '#2563eb' }} to="/grievances">View all →</Link>}>
          <div className="table-wrap">
            <table>
              <thead><tr><th>ID</th><th>Issue</th><th>Priority</th><th>Status</th><th>Age</th></tr></thead>
              <tbody>
                {queue.map((g) => (
                  <tr key={g.id} className="row" onClick={() => nav(`/grievances/${g.id}`)}>
                    <td className="mono">{g.id}</td>
                    <td><div style={{ fontWeight: 500 }}>{g.title}</div><div className="small muted">{g.category} · {g.department}</div></td>
                    <td><PriorityBadge level={g.priority_level} /><div className="small muted">{g.priority_score}/100</div></td>
                    <td><StatusBadge status={g.status} />{g.stage !== 'Complaint' && <div style={{ marginTop: 3 }}><StageBadge stage={g.stage} /></div>}</td>
                    <td className="small muted">{timeAgo(g.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <div className="grid">
          <Card title="Open cases by priority">
            <ResponsiveContainer width="100%" height={170}>
              <PieChart>
                <Pie data={an.by_priority} dataKey="value" nameKey="name" innerRadius={48} outerRadius={75} paddingAngle={2}>
                  {an.by_priority.map((p) => <Cell key={p.name} fill={PRIORITY_COLORS[p.name]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="row-flex" style={{ justifyContent: 'center' }}>
              {an.by_priority.map((p) => <span key={p.name} className="small"><span className="dot" style={{ background: PRIORITY_COLORS[p.name], boxShadow: 'none' }} />{p.name} {p.value}</span>)}
            </div>
          </Card>
          <div className="grid g2">
            <Stat icon={Timer} label="Avg resolution" value={fmtHours(s.avg_resolution_hours)} color="#0284c7" />
            <Stat icon={Star} label="Citizen rating" value={s.satisfaction} color="#d97706" />
          </div>
        </div>
      </div>
      <Card title="Grievances by category">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={an.by_category} margin={{ bottom: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" />
            <YAxis tick={{ fontSize: 11 }} width={30} />
            <Tooltip />
            <RBar dataKey="value" name="Grievances" fill="#2563eb" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </>
  )
}
