import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Camera, Search, ThumbsDown, ThumbsUp, Users } from 'lucide-react'
import { api, API_BASE, fmtHours, STAGE_COLORS, STATUS_COLORS } from '../api'
import { CitizenLogin, useCitizen } from '../components/Citizen'
import { Card, PriorityBadge, StageBadge, StageLadder, StatusBadge } from '../components/ui'
import { LangSwitch, useLang } from '../i18n'

const FLOW = ['Submitted', 'Assigned', 'In Progress', 'Resolved', 'Closed']

export default function Track() {
  const { id } = useParams()
  const nav = useNavigate()
  const [lang, t, setLang] = useLang()
  const me = useCitizen()
  const [q, setQ] = useState(id || '')
  const [g, setG] = useState(null)
  const [err, setErr] = useState(false)
  const [rated, setRated] = useState(0)
  const [comment, setComment] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (!id) return
    setErr(false); setG(null); setMsg('')
    api.track(id).then((d) => { setG(d); setRated(d.feedback_rating || 0) }).catch(() => setErr(true))
  }, [id])

  // "Not Satisfied" sends the issue back to work, so the bar drops back to In Progress
  const stage = g ? FLOW.indexOf(g.status === 'Not Satisfied' ? 'In Progress' : g.status) : -1
  const respond = (body) => { setMsg(''); api.feedback(g.id, body).then((d) => { setG(d); setRated(d.feedback_rating || 0) }).catch((e) => setMsg(e.message)) }
  const canRespond = g && ['Resolved', 'Closed'].includes(g.status)
  const how = { CITIZEN: t.youJoined, AI: t.aiJoined, OFFICER: t.officerJoined }

  return (
    <div style={{ maxWidth: 820, margin: '0 auto' }}>
      <div className="page-head"><div><h2>{t.trackTitle}</h2><p>{t.trackHint}</p></div><LangSwitch lang={lang} onChange={setLang} /></div>
      <Card>
        <form className="row-flex" onSubmit={(e) => { e.preventDefault(); nav(`/track/${q.trim()}`) }}>
          <input className="input" style={{ flex: 1 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="SS-2026-00001" />
          <button className="btn primary"><Search size={16} /> {t.trackBtn}</button>
        </form>
        {err && <p style={{ color: '#dc2626' }}>{t.notFound}</p>}
      </Card>
      {g && (
        <div className="grid" style={{ marginTop: 16 }}>
          <Card title={<span className="mono">{g.id}</span>} right={<StatusBadge status={g.status} label={t.status[g.status]} />}>
            <p style={{ marginTop: 0 }}>{g.text}</p>
            <div className="row-flex small muted"><PriorityBadge level={g.priority_level} label={t.level[g.priority_level]} /> {g.department} · {g.ward} · SLA {fmtHours(g.sla_hours)}
              {g.photo && <span className="chip"><Camera size={11} /> {t.photoAttached}</span>}
            </div>
            {(g.master_id !== g.id || g.report_count > 1) && (
              <div className="issue-card" style={{ margin: '12px 0 0' }}>
                <Users size={14} style={{ verticalAlign: -2 }} /> {g.master_id !== g.id && <>{t.partOf} <Link className="mono" style={{ textDecoration: 'underline' }} to={`/track/${g.master_id}`}>{g.master_id}</Link> ({how[g.association_source]}) · </>}
                <b>{g.report_count}</b> {t.reportsOn}
              </div>
            )}
            <div className="row-flex" style={{ marginTop: 22, gap: 0, flexWrap: 'nowrap' }}>
              {FLOW.map((s, i) => (
                <div key={s} style={{ flex: 1, textAlign: 'center' }}>
                  <div style={{ height: 6, background: i <= stage ? STATUS_COLORS[g.status] : '#e9ecef', borderRadius: 4, margin: '0 3px' }} />
                  <div className="small" style={{ marginTop: 6, fontWeight: i === stage ? 700 : 400, color: i <= stage ? '#1b2430' : '#8a949e' }}>{t.status[s] || s}</div>
                </div>
              ))}
            </div>
          </Card>
          <Card title={t.stage} right={<StageBadge stage={g.stage} label={t.stageName[g.stage]} />}>
            <StageLadder stages={g.stages} current={g.stage} labels={t.stageName} />
            <p style={{ marginBottom: 0 }}><span className="muted">{t.nowWith}:</span> <b style={{ color: STAGE_COLORS[g.stage] }}>{g.authority}</b>
              {g.stage_due && !['Resolved', 'Closed', 'Rejected'].includes(g.status) && <span className="small muted"> · {new Date(g.stage_due).toLocaleString()}</span>}
            </p>
          </Card>
          {g.resolution_photo && (
            <Card title={t.proof}><img className="evidence" alt="" src={`${API_BASE}/api/track/${encodeURIComponent(g.id)}/resolution-photo`} /></Card>
          )}
          {canRespond && (
            <Card title={t.confirmTitle} right={g.satisfaction && <span className="chip">{t.yourAnswer}: {g.satisfaction === 'Satisfied' ? t.satisfied : t.notSatisfied}</span>}>
              <p className="small muted" style={{ marginTop: 0 }}>{t.confirmHint}</p>
              {g.has_account && !me ? (
                <><p className="small">{t.needLogin}</p><CitizenLogin t={t} me={me} /></>
              ) : (
                <>
                  <div className="stars">{[1, 2, 3, 4, 5].map((n) => <button key={n} className={n <= rated ? 'on' : ''} onClick={() => setRated(n)}>★</button>)}</div>
                  <input className="input" style={{ margin: '8px 0' }} placeholder={t.comment} value={comment} onChange={(e) => setComment(e.target.value)} />
                  <div className="row-flex">
                    <button className="btn" style={{ color: '#16a34a' }} onClick={() => respond({ satisfied: true, rating: rated || null, comment: comment || null })}><ThumbsUp size={15} /> {t.satisfied}</button>
                    <button className="btn" style={{ color: '#dc2626' }} onClick={() => respond({ satisfied: false, rating: rated || null, comment: comment || null })}><ThumbsDown size={15} /> {t.notSatisfied}</button>
                  </div>
                </>
              )}
              {msg && <p className="small" style={{ color: '#dc2626', marginBottom: 0 }}>{msg}</p>}
            </Card>
          )}
          <Card title={t.updates}>
            <ul className="timeline">
              {g.timeline.map((e, i) => (
                <li key={i} style={{ '--c': STATUS_COLORS[e.status] || STAGE_COLORS[e.status] || '#d97706' }}>
                  <b className="small">{t.status[e.status] || t.stageName[e.status] || e.status}</b> <span className="small muted">· {new Date(e.ts).toLocaleString()} · {e.actor}</span>
                  <div style={{ fontSize: 14 }}>{e.note}</div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </div>
  )
}
