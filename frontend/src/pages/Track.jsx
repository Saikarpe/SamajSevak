import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Camera, CheckCircle2, CircleDashed, Clock, Search, Send, ThumbsDown, ThumbsUp, Users, XCircle } from 'lucide-react'
import { api, API_BASE, fmtHours, shrinkPhoto, STAGE_COLORS, STATUS_COLORS } from '../api'
import { CitizenLogin, useCitizen } from '../components/Citizen'
import { Card, PriorityBadge, StageBadge, StageLadder, StatusBadge } from '../components/ui'
import { LangSwitch, useLang } from '../i18n'

const FLOW = ['Submitted', 'Assigned', 'In Progress', 'Resolved', 'Closed']
const OUTCOME = {
  done: ['#16a34a', CheckCircle2], awaiting: ['#0d9488', CheckCircle2], not_done: ['#dc2626', XCircle],
  in_progress: ['#0284c7', Clock], rejected: ['#8a949e', XCircle], not_reached: ['#9aa5b1', CircleDashed],
}
const GROUND_COLORS = { yes: '#16a34a', partly: '#d97706', no: '#dc2626' }

// "Is work happening on the ground?" for the stage the issue is at now
function GroundAsk({ g, t, onSent }) {
  const [answer, setAnswer] = useState('')
  const [comment, setComment] = useState('')
  const [photo, setPhoto] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const pick = async (e) => { const f = e.target.files[0]; e.target.value = ''; if (f) try { setPhoto(await shrinkPhoto(f)) } catch { setErr('Could not read this image.') } }
  const send = () => {
    setBusy(true); setErr('')
    api.ground(g.id, { answer, comment: comment || null, photo }).then((d) => { setAnswer(''); setComment(''); setPhoto(null); onSent(d) })
      .catch((x) => setErr(x.message)).finally(() => setBusy(false))
  }
  return (
    <div className="ground-ask">
      <b className="small">{t.groundQ}</b>
      <div className="row-flex" style={{ marginTop: 6 }}>
        {['yes', 'partly', 'no'].map((a) => (
          <button key={a} type="button" className={`btn ${answer === a ? 'on' : ''}`} style={{ '--c': GROUND_COLORS[a] }} onClick={() => setAnswer(a)}>{t.ground[a]}</button>
        ))}
      </div>
      {answer && (
        <>
          <input className="input" style={{ margin: '8px 0' }} placeholder={t.groundPh} value={comment} onChange={(e) => setComment(e.target.value)} maxLength={500} />
          <div className="row-flex">
            <label className="btn" style={{ cursor: 'pointer' }}><Camera size={15} />{t.addPhoto}<input type="file" accept="image/*" hidden onChange={pick} /></label>
            {photo && <img src={photo} alt="" className="thumb" />}
            <button type="button" className="btn primary" disabled={busy} onClick={send}><Send size={15} /> {t.send}</button>
          </div>
          {answer === 'no' && <p className="small muted" style={{ marginBottom: 0 }}>{t.groundNoFlag}</p>}
        </>
      )}
      {err && <p className="small" style={{ color: '#dc2626', marginBottom: 0 }}>{err}</p>}
    </div>
  )
}

// one card per escalation stage: who held it, how long, what officers did, done or not, and the citizen's view
function StageReports({ g, t, me, onSent }) {
  const [sent, setSent] = useState(false)
  return (
    <Card title={t.stageReports}>
      <p className="small muted" style={{ marginTop: 0 }}>{t.stageReportsHint}</p>
      {g.stage_reports.map((c) => {
        const [color, Icon] = OUTCOME[c.outcome]
        const others = Object.entries(c.ground || {}).filter(([, n]) => n > 0)
        return (
          <div key={c.stage} className={`stage-report ${c.outcome}`} style={{ '--c': c.outcome === 'not_reached' ? '#d5dbe3' : STAGE_COLORS[c.stage] }}>
            <div className="row-flex between">
              <StageBadge stage={c.stage} label={t.stageName[c.stage]} />
              <span className="small" style={{ color, fontWeight: 600 }}><Icon size={14} style={{ verticalAlign: -2 }} /> {t.outcome[c.outcome]}</span>
            </div>
            <div className="small" style={{ marginTop: 6 }}><span className="muted">{t.heldBy}:</span> {c.holder}</div>
            {c.outcome !== 'not_reached' && (
              <>
                <div className="small muted">
                  {new Date(c.start).toLocaleString()}{c.end && ` → ${new Date(c.end).toLocaleString()}`} · {t.took}: {fmtHours(c.hours)}
                  {c.due && <> · {t.dueBy}: {new Date(c.due).toLocaleString()}</>}
                </div>
                <div className="small" style={{ marginTop: 4 }}>
                  <span className="muted">{t.officerActions}:</span> {c.actions ? <>{c.actions} · “{c.last_action}”</> : <span className="muted">{t.noActions}</span>}
                </div>
                {others.length > 0 && (
                  <div className="small" style={{ marginTop: 4 }}><span className="muted">{t.othersGround}:</span> {others.map(([a, n]) => <b key={a} style={{ color: GROUND_COLORS[a], marginRight: 8 }}>{n} {t.ground[a]}</b>)}</div>
                )}
                {c.mine && <div className="small" style={{ marginTop: 4 }}><span className="muted">{t.yourGround}:</span> <b style={{ color: GROUND_COLORS[c.mine.answer] }}>{t.ground[c.mine.answer]}</b>{c.mine.comment && ` · “${c.mine.comment}”`}</div>}
                {c.outcome === 'in_progress' && g.can_report_ground && (
                  g.has_account && !me
                    ? <div style={{ marginTop: 8 }}><p className="small" style={{ margin: '0 0 6px' }}>{t.needLogin}</p><CitizenLogin t={t} me={me} /></div>
                    : <><GroundAsk g={g} t={t} onSent={(d) => { setSent(true); onSent(d) }} />{sent && <p className="small" style={{ color: '#16a34a', marginBottom: 0 }}>{t.groundThanks}</p>}</>
                )}
              </>
            )}
          </div>
        )
      })}
    </Card>
  )
}

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
          {g.stage_reports && <StageReports g={g} t={t} me={me} onSent={setG} />}
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
