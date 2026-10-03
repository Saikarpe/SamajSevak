import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, session, timeAgo } from '../api'
import { Card, PriorityBadge, StageBadge, StatusBadge } from '../components/ui'

export default function Queue({ meta }) {
  const [params, setParams] = useSearchParams()
  const [rows, setRows] = useState(null)
  const nav = useNavigate()
  const me = session.get()
  const head = me?.role === 'department'
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
      <div className="page-head"><div><h2>{head ? `${me.department} — Queue` : 'Priority Queue'}</h2><p>One row per master issue, however many citizens reported it. Open issues ranked by AI priority score, then history.</p></div></div>
      {head && <div className="alert Medium" style={{ marginBottom: 16 }}><b>Your department's issues at the Complaint and Warning stages</b><p>Resolve them before the warning period ends. Once an issue reaches Strike 1 it moves to the strike bodies and leaves this queue.</p></div>}
      {me?.role === 'strike' && <div className="alert Medium" style={{ marginBottom: 16 }}><b>Strike body view: every department, every stage</b><p>Filter by department to check whether it is resolving its issues within the Complaint and Warning periods.</p></div>}
      <Card>
        <div className="row-flex" style={{ marginBottom: 12 }}>
          <input className="input" style={{ maxWidth: 260 }} placeholder="Search text or ID…" defaultValue={f.q || ''} onKeyDown={(e) => e.key === 'Enter' && set('q')(e)} />
          {sel('status', 'All statuses', meta?.statuses || [])}
          {sel('priority', 'All priorities', ['Critical', 'High', 'Medium', 'Low'])}
          {!head && sel('department', 'All departments', [...new Set(Object.values(meta?.categories || {}).map((c) => c.department))])}
          {sel('category', 'All categories', Object.keys(meta?.categories || {}))}
          {sel('ward', 'All wards', meta?.wards || [])}
          {sel('stage', 'All stages', (meta?.stages || []).map((x) => x.stage).filter((s) => !head || ['Complaint', 'Warning'].includes(s)))}
          {f.flagged && <button className="btn" onClick={() => { const p = new URLSearchParams(params); p.delete('flagged'); setParams(p) }}>Flagged for review — clear</button>}
          <span className="small muted">{rows ? `${rows.length} results` : 'Loading…'}</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Grievance</th><th>Ward</th><th>Department</th><th>Priority</th><th>Status</th><th>Stage · with</th><th>Received</th></tr></thead>
            <tbody>
              {rows?.map((g) => (
                <tr key={g.id} className="row" onClick={() => nav(`/grievances/${g.id}`)}>
                  <td className="mono">{g.id}</td>
                  <td style={{ maxWidth: 340 }}><div style={{ fontWeight: 500 }}>{g.title}</div><div className="small muted">{g.category}{g.report_count > 1 && <b style={{ color: '#2563eb' }}> · {g.report_count} reports</b>}{g.duplicate_of && g.report_count === 1 && ' · possible duplicate'}{g.language && g.language !== 'English' && ` · ${g.language}`}{g.photo && ' · photo'}{g.any_abuse_review ? ' · review flag' : ''}</div></td>
                  <td>{g.ward}</td>
                  <td className="small">{g.department}</td>
                  <td><PriorityBadge level={g.priority_level} /><div className="small muted">{g.priority_score}</div></td>
                  <td><StatusBadge status={g.status} />{g.status === 'Resolved' && <div className="small muted">awaiting citizen</div>}</td>
                  <td><StageBadge stage={g.stage} /><div className="small muted" style={{ maxWidth: 190 }}>{g.authority}</div></td>
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
