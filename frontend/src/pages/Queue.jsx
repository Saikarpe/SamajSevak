import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, timeAgo } from '../api'
import { Card, PriorityBadge, StatusBadge } from '../components/ui'

export default function Queue({ meta }) {
  const [params, setParams] = useSearchParams()
  const [rows, setRows] = useState(null)
  const nav = useNavigate()
  const f = Object.fromEntries(params)
  useEffect(() => { setRows(null); api.list({ ...f, limit: 300 }).then(setRows) }, [params.toString()])
  const set = (k) => (e) => { const p = new URLSearchParams(params); e.target.value ? p.set(k, e.target.value) : p.delete(k); setParams(p) }
  const sel = (k, label, opts) => (
    <select className="input" style={{ width: 'auto' }} value={f[k] || ''} onChange={set(k)}>
      <option value="">{label}</option>{opts.map((o) => <option key={o}>{o}</option>)}
    </select>
  )
  return (
    <>
      <div className="page-head"><div><h2>Priority Queue</h2><p>Open cases ranked by AI priority score, then resolved history.</p></div></div>
      <Card>
        <div className="row-flex" style={{ marginBottom: 12 }}>
          <input className="input" style={{ maxWidth: 260 }} placeholder="Search text or ID…" defaultValue={f.q || ''} onKeyDown={(e) => e.key === 'Enter' && set('q')(e)} />
          {sel('status', 'All statuses', meta?.statuses || [])}
          {sel('priority', 'All priorities', ['Critical', 'High', 'Medium', 'Low'])}
          {sel('category', 'All categories', Object.keys(meta?.categories || {}))}
          {sel('ward', 'All wards', meta?.wards || [])}
          <span className="small muted">{rows ? `${rows.length} results` : 'Loading…'}</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Grievance</th><th>Ward</th><th>Department</th><th>Priority</th><th>Status</th><th>Channel</th><th>Received</th></tr></thead>
            <tbody>
              {rows?.map((g) => (
                <tr key={g.id} className="row" onClick={() => nav(`/grievances/${g.id}`)}>
                  <td className="mono">{g.id}</td>
                  <td style={{ maxWidth: 340 }}><div style={{ fontWeight: 500 }}>{g.title}</div><div className="small muted">{g.category}{g.duplicate_of && ' · possible duplicate'}</div></td>
                  <td>{g.ward}</td>
                  <td className="small">{g.department}</td>
                  <td><PriorityBadge level={g.priority_level} /><div className="small muted">{g.priority_score}</div></td>
                  <td><StatusBadge status={g.status} />{g.sla_breached && g.status !== 'Resolved' && <div className="small" style={{ color: '#dc2626' }}>SLA breached</div>}</td>
                  <td className="small">{g.channel}</td>
                  <td className="small muted">{timeAgo(g.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
