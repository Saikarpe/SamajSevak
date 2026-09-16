import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Bot, CheckCircle2, ClipboardCopy, Loader2, Play, UserCheck } from 'lucide-react'
import { api, fmtHours, STATUS_COLORS } from '../api'
import AnalysisPanel from '../components/AnalysisPanel'
import { Card, PriorityBadge, StatusBadge } from '../components/ui'

export default function Detail({ meta }) {
  const { id } = useParams()
  const [g, setG] = useState(null)
  const [draft, setDraft] = useState(null)
  const [drafting, setDrafting] = useState(false)
  const [note, setNote] = useState('')
  const [officer, setOfficer] = useState('')

  useEffect(() => { setG(null); setDraft(null); api.get(id).then(setG) }, [id])
  if (!g) return <div className="empty pulse">Loading grievance…</div>

  const act = async (body) => { setG({ ...(await api.update(g.id, body)), live_similar: g.live_similar }); setNote('') }
  const genDraft = async () => { setDrafting(true); try { setDraft(await api.draft(g.id)) } finally { setDrafting(false) } }
  const a = { ...g.analysis, similar_cases: g.live_similar || g.analysis.similar_cases }
  const open = !['Resolved', 'Rejected'].includes(g.status)

  return (
    <>
      <Link to="/grievances" className="small muted row-flex" style={{ marginBottom: 10 }}><ArrowLeft size={14} /> Back to queue</Link>
      <div className="page-head">
        <div>
          <div className="row-flex"><span className="mono muted">{g.id}</span><StatusBadge status={g.status} /><PriorityBadge level={g.priority_level} />{g.sla_breached && open && <span className="chip red">SLA breached</span>}</div>
          <h2 style={{ marginTop: 6 }}>{g.title}</h2>
          <p>{g.ward} · via {g.channel} · {new Date(g.created_at).toLocaleString()} · SLA due {new Date(g.sla_due).toLocaleString()}</p>
        </div>
      </div>
      <div className="grid g-main" style={{ alignItems: 'start' }}>
        <div className="grid">
          <Card title="Citizen complaint">
            <p style={{ marginTop: 0, fontSize: 15, lineHeight: 1.6 }}>“{g.text}”</p>
            <div className="small muted">{g.citizen_name || 'Anonymous'} {g.phone && `· ${g.phone.slice(0, 4)}xxxx${g.phone.slice(-2)}`}</div>
          </Card>
          <AnalysisPanel a={a} />
        </div>
        <div className="grid" style={{ position: 'sticky', top: 16 }}>
          <Card title="Officer actions">
            <dl className="kv" style={{ marginBottom: 12 }}>
              <dt>Department</dt><dd>{g.department}</dd>
              <dt>Assigned to</dt><dd>{g.assigned_to || '—'}</dd>
              {g.resolution_hours && <><dt>Resolved in</dt><dd>{fmtHours(g.resolution_hours)}</dd></>}
              {g.resolution_note && <><dt>Resolution</dt><dd>{g.resolution_note}</dd></>}
              {g.feedback_rating && <><dt>Citizen rating</dt><dd>{'★'.repeat(g.feedback_rating)}</dd></>}
            </dl>
            {open && (
              <>
                <div className="field">
                  <label>Assign field officer</label>
                  <div className="row-flex" style={{ flexWrap: 'nowrap' }}>
                    <input className="input" value={officer} onChange={(e) => setOfficer(e.target.value)} placeholder="e.g. JE R. Kulkarni" />
                    <button className="btn" disabled={!officer} onClick={() => act({ assigned_to: officer, status: 'Assigned', note: `Assigned to ${officer}` })}><UserCheck size={15} /></button>
                  </div>
                </div>
                <div className="field">
                  <label>Update note / resolution</label>
                  <textarea className="input" style={{ minHeight: 70 }} value={note} onChange={(e) => setNote(e.target.value)} placeholder={a.recommendation?.proven_resolutions?.[0]?.action || 'Describe action taken'} />
                </div>
                <div className="row-flex">
                  <button className="btn primary" onClick={() => act({ status: 'In Progress', note: note || 'Field team dispatched' })}><Play size={15} /> Start work</button>
                  <button className="btn" style={{ color: '#16a34a' }} onClick={() => act({ status: 'Resolved', resolution_note: note || a.recommendation?.proven_resolutions?.[0]?.action || 'Resolved', note })}><CheckCircle2 size={15} /> Resolve</button>
                  <button className="btn" style={{ color: '#6b7280' }} onClick={() => act({ status: 'Rejected', note: note || 'Not under municipal jurisdiction' })}>Reject</button>
                </div>
              </>
            )}
          </Card>
          <Card title={<><Bot size={18} color="#4f46e5" /> AI response draft</>} sub={draft ? `via ${draft.provider}` : ''}>
            {!draft && <button className="btn primary" onClick={genDraft} disabled={drafting}>{drafting ? <Loader2 size={15} className="pulse" /> : <Bot size={15} />} Generate citizen reply</button>}
            {draft && (
              <>
                <div className="pre">{draft.text}</div>
                <button className="btn" style={{ marginTop: 10 }} onClick={() => navigator.clipboard?.writeText(draft.text)}><ClipboardCopy size={15} /> Copy</button>
              </>
            )}
          </Card>
          <Card title="Audit trail">
            <ul className="timeline">
              {g.timeline.map((t, i) => (
                <li key={i} style={{ '--c': STATUS_COLORS[t.status] || '#f59e0b' }}>
                  <b className="small">{t.status}</b> <span className="small muted">· {new Date(t.ts).toLocaleString()}</span>
                  <div className="small">{t.note}</div><div className="small muted">{t.actor}</div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
