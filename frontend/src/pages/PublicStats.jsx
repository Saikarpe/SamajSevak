import { useEffect, useState } from 'react'
import { CheckCircle2, Hourglass, Inbox, Layers, Users } from 'lucide-react'
import { api, fmtHours, STAGE_COLORS } from '../api'
import { Card, Stat } from '../components/ui'

// Aggregate counts only: no complaint text, names, photos or locations. No scores or rankings of anyone.
export default function PublicStats() {
  const [s, setS] = useState(null)
  useEffect(() => { api.publicStats().then(setS) }, [])
  if (!s) return <div className="empty pulse">Loading…</div>
  const table = (rows, label) => (
    <div className="table-wrap">
      <table>
        <thead><tr><th>{label}</th><th>Issues received</th><th>Resolved</th><th>Pending</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.name}><td>{r.name}</td><td>{r.received}</td><td>{r.resolved}</td><td>{r.pending}</td></tr>)}</tbody>
      </table>
    </div>
  )
  return (
    <>
      <div className="page-head"><div><h2>Public accountability</h2><p>Factual operational counts. This build runs on seeded demo data, not real complaints.</p></div></div>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <Stat icon={Inbox} label="Citizen reports received" value={s.reports_received} hint={`${s.issues} distinct issues`} />
        <Stat icon={CheckCircle2} label="Issues resolved" value={s.issues_resolved} color="#16a34a" hint={`${s.issues_confirmed_by_citizens} confirmed by citizens`} />
        <Stat icon={Hourglass} label="Issues pending" value={s.issues_pending} color="#ea580c" hint={`${s.not_satisfied} reopened by citizens`} />
        <Stat icon={Users} label="Issues reported by several citizens" value={s.multi_report_issues} color="#2563eb" hint={`${s.linked_reports} supporting reports`} />
      </div>
      <Card title={<><Layers size={18} color="#2563eb" /> Pending issues by escalation stage</>} sub={`average resolution time ${fmtHours(s.avg_resolution_hours)}`} style={{ marginBottom: 16 }}>
        <div className="stage-row">
          {Object.entries(s.stages).map(([stage, n]) => <button key={stage} style={{ borderTopColor: STAGE_COLORS[stage], cursor: 'default' }}><b>{n}</b><span>{stage}</span></button>)}
        </div>
        <p className="small muted" style={{ marginBottom: 0 }}>Complaint and Warning are handled by the concerned department. Strike 1: higher authority of that department. Strike 2: Deputy Collector. Strike 3: final escalation body. This ladder is the prototype’s own workflow, not a statutory procedure.</p>
      </Card>
      <div className="grid g2">
        <Card title="By department">{table(s.by_department, 'Department')}</Card>
        <Card title="By ward">{table(s.by_ward, 'Ward')}</Card>
      </div>
    </>
  )
}
