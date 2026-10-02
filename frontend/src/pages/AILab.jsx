import { useEffect, useState } from 'react'
import { ArrowRight, Brain, Copy, FileSearch, Gauge, Languages, Lightbulb, MessageSquareText, Radar, RefreshCw, Tags } from 'lucide-react'
import { api } from '../api'
import { Card } from '../components/ui'

const STAGES = [
  { icon: Languages, t: 'Ingest & Clean', d: 'Web form with voice, GPS / map pin and photo. Detects English, Hinglish, Hindi and Marathi (Devanagari); strips greetings/boilerplate.' },
  { icon: Tags, t: 'Classify & Route', d: 'Two models averaged: TF-IDF word + char n-grams and multilingual sentence embeddings → Logistic Regression over 11 categories; maps to department & SLA. Low confidence → human triage.' },
  { icon: FileSearch, t: 'Extract Entities', d: 'Ward, landmark, issue duration, risk keywords and vulnerable groups (children, elderly, patients…) from English, Hindi and Marathi lexicons.' },
  { icon: MessageSquareText, t: 'Sentiment & Distress', d: 'Lexicon-based sentiment with intensifiers, exclamation & caps signals → emotion and distress score.' },
  { icon: Copy, t: 'Duplicate Detection', d: 'Meaning-level similarity (embeddings, works across languages) + TF-IDF, then GPS distance: within 300 m = same incident. Falls back to same ward when a report has no GPS.' },
  { icon: Gauge, t: 'Explainable Priority', d: 'Transparent 0–100 score: severity + risk + vulnerability + distress + duration + cluster size + repeat complaint.' },
  { icon: Lightbulb, t: 'Recommend Resolution', d: 'Context-ranked SOP playbook + proven actions retrieved from similar resolved cases + ETA from historical resolution times.' },
  { icon: Radar, t: 'Detect Emerging Issues', d: 'Ward × category spike detection vs 3-week baseline → systemic root-cause alerts and SLA-breach escalation.' },
  { icon: Brain, t: 'GenAI Assist (optional)', d: 'Gemini / OpenAI drafts citizen replies and checks photo evidence against the complaint; template fallback keeps it working offline.' },
]
const pct = (x) => (x != null ? `${(x * 100).toFixed(1)}%` : '—')

export default function AILab({ meta }) {
  const [m, setM] = useState(null)
  const [info, setInfo] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  useEffect(() => { api.model().then(setInfo).catch(() => {}) }, [])
  const metrics = m || meta?.model_metrics || {}
  const pending = info ? info.verified_labels - info.trained_on_verified : 0
  const retrain = async () => {
    setBusy(true); setMsg('')
    try {
      const r = await api.retrain()
      setM((await api.meta()).model_metrics); setInfo(await api.model())
      setMsg(`Retrained with ${r.verified_rows} officer-verified complaint(s). Holdout accuracy ${pct(r.holdout_accuracy)}.`)
    } catch (e) { setMsg(e.message) } finally { setBusy(false) }
  }
  return (
    <>
      <div className="page-head"><div><h2>AI Engine</h2><p>How SamajSevak turns raw complaints into prioritised, actionable decisions.</p></div></div>
      <div className="grid g3" style={{ marginBottom: 16 }}>
        {STAGES.map((s, i) => (
          <Card key={s.t}>
            <div className="row-flex" style={{ marginBottom: 6 }}>
              <div className="stat-icon" style={{ background: '#e8f0fe', color: '#2563eb', width: 36, height: 36 }}><s.icon size={18} /></div>
              <b>{i + 1}. {s.t}</b>{i < STAGES.length - 1 && <ArrowRight size={14} className="muted" style={{ marginLeft: 'auto' }} />}
            </div>
            <div className="small muted" style={{ lineHeight: 1.55 }}>{s.d}</div>
          </Card>
        ))}
      </div>
      <div className="grid g2">
        <div className="grid">
          <Card title="Classifier evaluation" sub={metrics.embeddings ? 'TF-IDF + multilingual embeddings' : 'TF-IDF only (embeddings unavailable)'}>
            <dl className="kv" style={{ gridTemplateColumns: '190px 1fr' }}>
              <dt>Training samples</dt><dd>{metrics.train_size ?? '—'} (+{metrics.test_size ?? '—'} test) · {metrics.classes?.length ?? '—'} categories</dd>
              <dt>Synthetic test split</dt><dd>{pct(metrics.test_accuracy)} <span className="small muted">(easy by design)</span></dd>
              <dt>English + Hinglish holdout</dt><dd>{pct(metrics.holdout_accuracy)} on {metrics.holdout_size} hand-written complaints <span className="small muted">(TF-IDF alone: {pct(metrics.holdout_accuracy_tfidf_only)})</span></dd>
              {Object.entries(metrics.languages || {}).map(([name, s]) => (
                <div key={name} style={{ display: 'contents' }}>
                  <dt>{name} (Devanagari)</dt>
                  <dd>{pct(s.accuracy)} on {s.size} <span className="small muted">· {pct(metrics.zero_shot?.[name]?.accuracy)} before any {name} training text was added</span></dd>
                </div>
              ))}
              {metrics.probe && <><dt>Other languages (probe)</dt><dd className="small">{Object.entries(metrics.probe).map(([n, s]) => `${n} ${Math.round(s.accuracy * s.size)}/${s.size}`).join(' · ')} <span className="muted">— no templates, sent to human review</span></dd></>}
            </dl>
            <p className="small muted">The synthetic split is easy by design; the hand-written holdout is the realistic check. The Hindi / Marathi sets were written before their training templates, but by the same author, so treat them as optimistic. Below 40% confidence a case goes to human triage.</p>
          </Card>
          <Card title="Learning from officers" sub="real complaints, human labels">
            <dl className="kv" style={{ gridTemplateColumns: '190px 1fr' }}>
              <dt>Officer-verified labels</dt><dd>{info?.verified_labels ?? '—'} <span className="small muted">({info?.trained_on_verified ?? 0} already in the model, {pending} new)</span></dd>
            </dl>
            <p className="small muted">Each time an officer confirms or corrects a category on a case, that complaint becomes a real training example, weighted 10× a synthetic one. Retraining takes about a minute and swaps the model in without a restart.</p>
            <button className="btn primary" onClick={retrain} disabled={busy}><RefreshCw size={15} className={busy ? 'pulse' : ''} /> {busy ? 'Retraining…' : 'Retrain classifier now'}</button>
            {msg && <p className="small" style={{ marginBottom: 0 }}>{msg}</p>}
          </Card>
        </div>
        <Card title="Categories → Departments → SLA">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Category</th><th>Department</th><th>SLA</th></tr></thead>
              <tbody>{Object.entries(meta?.categories || {}).map(([k, v]) => <tr key={k}><td>{k}</td><td className="small">{v.department}</td><td>{v.sla_hours} h</td></tr>)}</tbody>
            </table>
          </div>
        </Card>
      </div>
    </>
  )
}
