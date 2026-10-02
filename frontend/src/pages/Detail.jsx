import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Bot, Camera, CheckCircle2, ClipboardCopy, Flag, Layers, Loader2, MapPin, Play, Tags, UserCheck, Users, X } from 'lucide-react'
import { api, fmtHours, isOpen, shrinkPhoto, STAGE_COLORS, STATUS_COLORS } from '../api'
import AnalysisPanel from '../components/AnalysisPanel'
import { Card, PriorityBadge, StageBadge, StageLadder, StatusBadge } from '../components/ui'

const GEO = { gps: 'GPS fix from the citizen’s phone', pin: 'Pin placed on the map by the citizen', seed: 'GPS fix (simulated seed data)', ward: 'Ward centre only — no GPS shared' }
const SOURCE = { CITIZEN: 'joined by the citizen', AI: 'matched by AI', OFFICER: 'linked by an officer' }

function Evidence({ id }) {
  const [src, setSrc] = useState(null)
  useEffect(() => { api.photo(id).then(setSrc).catch(() => {}) }, [id])
  return src ? <img className="evidence" src={src} alt={`Photo attached to ${id}`} style={{ maxHeight: 220, marginTop: 6 }} /> : null
}

export default function Detail({ meta }) {
  const { id } = useParams()
  const [g, setG] = useState(null)
  const [draft, setDraft] = useState(null)
  const [drafting, setDrafting] = useState(false)
  const [note, setNote] = useState('')
  const [officer, setOfficer] = useState('')
  const [category, setCategory] = useState('')
  const [proof, setProof] = useState(null)
  const [linkTo, setLinkTo] = useState('')
  const [err, setErr] = useState('')

  const load = () => api.get(id).then((d) => { setG(d); setCategory(d.category) })
  useEffect(() => { setG(null); setDraft(null); setProof(null); setErr(''); load() }, [id])
  if (!g) return <div className="empty pulse">Loading grievance…</div>

  // officer actions go to the master issue; the API applies them there even from a linked report
  const act = (body, target = g.id) => api.update(target, body).then(() => { setNote(''); setProof(null); setLinkTo(''); setErr(''); load() }).catch((e) => setErr(e.message))
  const genDraft = async () => { setDrafting(true); try { setDraft(await api.draft(g.id)) } finally { setDrafting(false) } }
  const pickProof = async (e) => { const f = e.target.files[0]; e.target.value = ''; if (f) setProof(await shrinkPhoto(f)) }
  const a = { ...g.analysis, similar_cases: g.live_similar || g.analysis.similar_cases, possible_duplicates: g.live_duplicates || g.analysis.possible_duplicates }
  const open = isOpen(g.status)
  const check = g.photo_check
  const isMaster = g.master_id === g.id
  const stages = (meta?.stages || []).map((s) => s.stage)
  const next = meta?.stages?.[stages.indexOf(g.stage) + 1]
  const flagged = g.reports.filter((r) => r.abuse_review)

  return (
    <>
      <Link to="/grievances" className="small muted row-flex" style={{ marginBottom: 10 }}><ArrowLeft size={14} /> Back to queue</Link>
      <div className="page-head">
        <div>
          <div className="row-flex"><span className="mono muted">{g.id}</span><StatusBadge status={g.status} /><StageBadge stage={g.stage} /><PriorityBadge level={g.priority_level} />{g.sla_breached && open && <span className="chip red">SLA breached</span>}{g.report_count > 1 && <span className="chip"><Users size={11} /> {g.report_count} citizen reports</span>}</div>
          <h2 style={{ marginTop: 6 }}>{g.title}</h2>
          <p>{g.ward} · via {g.channel} · {new Date(g.created_at).toLocaleString()} · SLA due {new Date(g.sla_due).toLocaleString()}</p>
        </div>
      </div>
      {!isMaster && (
        <div className="issue-card">
          This report is part of master issue <Link className="mono" style={{ textDecoration: 'underline' }} to={`/grievances/${g.master_id}`}>{g.master_id}</Link> ({SOURCE[g.association_source]}{g.association_note && `: ${g.association_note}`}). Status, assignment and resolution are handled on the master issue.
          <div className="row-flex" style={{ marginTop: 8 }}>
            {g.association_source !== 'OFFICER' && <button className="btn" onClick={() => act({ master_id: g.master_id })}>Confirm this link</button>}
            <button className="btn" onClick={() => act({ master_id: g.id })}>Not the same issue — detach</button>
          </div>
        </div>
      )}
      <div className="grid g-main" style={{ alignItems: 'start' }}>
        <div className="grid">
          <Card title="Citizen complaint">
            <p style={{ marginTop: 0, fontSize: 15, lineHeight: 1.6 }}>“{g.text}”</p>
            <div className="small muted">Citizen {g.citizen_id || 'not signed in'} <span title="Name and phone number are never shown in the officer console">· identity hidden</span></div>
            <div className="small muted" style={{ marginTop: 6 }}>
              <MapPin size={12} style={{ verticalAlign: -2 }} /> {GEO[g.geo_source] || GEO.ward}
              {g.geo_source !== 'ward' && g.geo_source && <> · <a href={`https://www.openstreetmap.org/?mlat=${g.lat}&mlon=${g.lng}#map=18/${g.lat}/${g.lng}`} target="_blank" rel="noreferrer" style={{ textDecoration: 'underline' }}>{g.lat.toFixed(5)}, {g.lng.toFixed(5)}</a></>}
            </div>
            {g.photo && <Evidence id={g.id} />}
            {g.photo && (
              <p className="small muted" style={{ marginBottom: 0 }}>
                {check?.seen ? <><b style={{ color: check.matches ? '#16a34a' : '#ea580c' }}>{check.matches ? 'AI photo check: consistent with the complaint' : 'AI photo check: photo does not clearly show the reported issue'}</b> — “{check.seen}” (via {check.provider}, advisory only)</>
                  : check?.error ? `AI photo check failed (${check.error}); review the photo manually.`
                    : meta?.llm_provider ? 'AI photo check is running — reload in a few seconds.' : 'Photo attached by the citizen. Automatic photo check needs a Gemini / OpenAI key; without one it is for the officer to review.'}
              </p>
            )}
          </Card>
          {(g.report_count > 1 || isMaster) && (
            <Card title={<><Users size={18} color="#2563eb" /> Master issue {g.master_id}</>} sub={`${g.report_count} citizen report(s), one workload`}>
              {g.reports.map((r) => (
                <div className="report" key={r.id}>
                  <div className="row-flex between">
                    <span><Link className="mono" style={{ textDecoration: 'underline' }} to={`/grievances/${r.id}`}>{r.id}</Link> <span className="small muted">· {new Date(r.created_at).toLocaleString()} · {r.channel} · citizen {r.citizen_id || '—'}</span></span>
                    <span>
                      {r.id === g.master_id ? <span className="chip">first report</span> : <span className="chip">{SOURCE[r.association_source]}</span>}
                      {r.satisfaction && <span className={`chip ${r.satisfaction === 'Satisfied' ? '' : 'red'}`}>{r.satisfaction}{r.feedback_rating ? ` ${'★'.repeat(r.feedback_rating)}` : ''}</span>}
                      {r.abuse_review ? <span className="chip warn"><Flag size={11} /> review</span> : null}
                    </span>
                  </div>
                  <div>“{r.text}”</div>
                  {r.association_note && <div className="small muted">Evidence for the link: {r.association_note}</div>}
                  {r.feedback_text && <div className="small muted">Citizen comment: “{r.feedback_text}”</div>}
                  {r.photo && r.id !== g.id ? <Evidence id={r.id} /> : null}
                  {r.id !== g.master_id && isMaster && <button className="btn" style={{ marginTop: 6 }} onClick={() => act({ master_id: r.id }, r.id)}>Not the same issue — detach</button>}
                </div>
              ))}
              <div className="row-flex" style={{ marginTop: 10, flexWrap: 'nowrap' }}>
                <input className="input" placeholder="Link this issue into another: SS-2026-…" value={linkTo} onChange={(e) => setLinkTo(e.target.value)} />
                <button className="btn" disabled={!linkTo.trim()} onClick={() => act({ master_id: linkTo.trim() })}>Link</button>
              </div>
              <span className="small muted">Linking, confirming and detaching are recorded in the audit trail. Reports are never deleted.</span>
            </Card>
          )}
          <AnalysisPanel a={a} />
        </div>
        <div className="grid" style={{ position: 'sticky', top: 16 }}>
          <Card title={<><Layers size={18} color={STAGE_COLORS[g.stage]} /> Escalation</>} right={<StageBadge stage={g.stage} />}>
            {stages.length > 0 && <StageLadder stages={stages} current={g.stage} />}
            <dl className="kv" style={{ marginTop: 12 }}>
              <dt>Now with</dt><dd>{g.authority}</dd>
              {open && g.stage_due && next && <><dt>Next</dt><dd>{next.stage} on {new Date(g.stage_due).toLocaleString()} <span className="small muted">→ {next.authority === 'Concerned department' ? `stays with ${g.department}` : next.authority}</span></dd></>}
              {!open && <><dt>Clock</dt><dd className="small">{g.status === 'Resolved' ? 'Paused: awaiting citizen confirmation. “Not satisfied” restarts it.' : 'Stopped'}</dd></>}
            </dl>
          </Card>
          <Card title="Officer actions">
            {err && <p className="small" style={{ color: '#dc2626', marginTop: 0 }}>{err}</p>}
            <dl className="kv" style={{ marginBottom: 12 }}>
              <dt>Department</dt><dd>{g.department}</dd>
              <dt>Assigned to</dt><dd>{g.assigned_to || '—'}</dd>
              {g.resolution_hours && <><dt>Resolved in</dt><dd>{fmtHours(g.resolution_hours)}</dd></>}
              {g.resolution_note && <><dt>Resolution</dt><dd>{g.resolution_note}</dd></>}
              {g.resolution_photo && <><dt>Photo proof</dt><dd>Attached, visible to the citizen</dd></>}
            </dl>
            <div className="field">
              <label><Tags size={13} style={{ verticalAlign: -2 }} /> Category</label>
              <div className="small" style={{ marginBottom: 4 }}>
                AI: <b>{g.ai_category || '—'}</b>{g.citizen_category && <> · Citizen: <b>{g.citizen_category}</b></>} · Final: <b>{g.category}</b> <span className="muted">(decided by {(g.classification_source || 'AI').toLowerCase()})</span>
                {g.citizen_category && g.ai_category && g.citizen_category !== g.ai_category && <span className="chip warn">AI and citizen disagree</span>}
              </div>
              <div className="row-flex" style={{ flexWrap: 'nowrap' }}>
                <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
                  {Object.keys(meta?.categories || { [g.category]: 1 }).map((c) => <option key={c}>{c}</option>)}
                </select>
                <button className="btn" onClick={() => act({ category })}>{category === g.category ? 'Confirm' : 'Correct'}</button>
              </div>
              <span className="small muted">Confirmed and corrected categories become real training data for the classifier.</span>
            </div>
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
                  <div className="row-flex">
                    <label className="btn" style={{ cursor: 'pointer' }}><Camera size={15} />{proof ? 'Change proof photo' : 'Add proof photo'}
                      <input type="file" accept="image/*" hidden onChange={pickProof} />
                    </label>
                    {proof && <><img src={proof} alt="" className="thumb" /><button className="btn" onClick={() => setProof(null)}><X size={14} /></button></>}
                  </div>
                </div>
                <div className="row-flex">
                  <button className="btn primary" onClick={() => act({ status: 'In Progress', note: note || 'Field team dispatched' })}><Play size={15} /> Start work</button>
                  <button className="btn" style={{ color: '#16a34a' }} onClick={() => act({ status: 'Resolved', resolution_note: note || a.recommendation?.proven_resolutions?.[0]?.action || 'Resolved', note, resolution_photo: proof })}><CheckCircle2 size={15} /> Resolve</button>
                  <button className="btn" style={{ color: '#5c6773' }} disabled={!note} title="A reason is required" onClick={() => act({ status: 'Rejected', note })}>Reject as invalid</button>
                </div>
                <span className="small muted">Resolve asks every citizen on the issue to confirm. Rejecting needs a written reason and keeps the record.</span>
              </>
            )}
          </Card>
          {flagged.length > 0 && (
            <Card title={<><Flag size={18} color="#ea580c" /> Abuse review</>} sub="signals, not proof">
              {(g.review_signals || []).map((s) => <div className="small" key={s}>• {s}</div>)}
              <p className="small muted" style={{ marginBottom: 0 }}>{flagged.map((r) => r.id).join(', ')} flagged because two or more signals coincided. Nothing was rejected automatically; a shared network or a reused photo can be legitimate. Network addresses are not shown.</p>
            </Card>
          )}
          <Card title={<><Bot size={18} color="#2563eb" /> AI response draft</>} sub={draft ? `via ${draft.provider}` : ''}>
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
                <li key={i} style={{ '--c': STATUS_COLORS[t.status] || STAGE_COLORS[t.status] || '#d97706' }}>
                  <b className="small">{t.status}</b> <span className="small muted">· {new Date(t.ts).toLocaleString()}</span>
                  <div className="small">{t.note}</div>
                  <div className="small muted">{t.actor}{t.actor_type && t.actor_type !== t.actor && ` (${t.actor_type})`}{t.prev_state && t.new_state && ` · ${t.prev_state} → ${t.new_state}`}</div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  )
}
