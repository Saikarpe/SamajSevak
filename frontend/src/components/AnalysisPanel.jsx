import { AlertTriangle, Brain, Building2, Copy, Gauge, History, Lightbulb, Link2, Smile, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PRIORITY_COLORS, fmtDistance, fmtHours } from '../api'
import { Bar, Card, PriorityBadge, ScoreRing, StatusBadge } from './ui'

// compact = citizen preview: similar cases are shown but do not link into the officer console
export default function AnalysisPanel({ a, compact = false }) {
  if (!a) return null
  const e = a.entities
  const rec = a.recommendation
  const maxPts = 30
  const dup = a.possible_duplicates?.[0]
  const partial = a.language?.support === 'partial'
  const Row = compact ? 'div' : Link
  return (
    <div className="grid">
      <Card title={<><Brain size={18} color="#2563eb" /> AI Triage</>} right={a.needs_human_review && <span className="chip warn">Needs human review</span>}>
        <div className="row-flex" style={{ gap: 18, alignItems: 'flex-start' }}>
          <ScoreRing score={a.priority_score} level={a.priority_level} />
          <dl className="kv" style={{ flex: 1, minWidth: 220 }}>
            <dt>Priority</dt><dd><PriorityBadge level={a.priority_level} /></dd>
            <dt>Category</dt><dd>{a.category} <span className="muted small">({Math.round(a.confidence * 100)}% confidence)</span></dd>
            <dt>Route to</dt><dd><Building2 size={14} style={{ verticalAlign: -2 }} /> {a.department}</dd>
            <dt>Ward</dt><dd>{a.ward || <span className="muted">Not detected</span>}</dd>
            {a.language && <><dt>Language</dt><dd>{a.language.name} <span className="muted small">({a.language.script} script)</span></dd></>}
            <dt>ETA</dt><dd>{fmtHours(rec.estimated_resolution_hours)} <span className="muted small">(SLA {fmtHours(rec.sla_hours)})</span></dd>
          </dl>
        </div>
        {a.alternatives?.length > 0 && (
          <div className="small muted" style={{ marginTop: 10 }}>
            Other possibilities: {a.alternatives.map((x) => `${x.category} ${Math.round(x.confidence * 100)}%`).join(' · ')}
          </div>
        )}
        {partial && (
          <div className="small" style={{ marginTop: 10, color: '#9a4a00' }}>
            {a.language.name} is read through multilingual embeddings only: the category is a suggestion and risk keywords were not checked, so an officer must confirm the priority.
          </div>
        )}
      </Card>

      <Card title={<><Gauge size={18} color="#ea580c" /> Why this priority?</>} sub="Explainable scoring">
        {a.priority_factors.map((f, i) => (
          <div className="factor" key={i}>
            <span>{f.factor}</span>
            <Bar value={f.points} max={maxPts} color={PRIORITY_COLORS[a.priority_level]} />
            <b style={{ textAlign: 'right' }}>+{f.points}</b>
          </div>
        ))}
      </Card>

      <div className={compact ? 'grid' : 'grid g2'}>
        <Card title={<><Smile size={18} color="#0284c7" /> Sentiment & Signals</>}>
          <dl className="kv">
            <dt>Sentiment</dt><dd>{a.sentiment.label} <span className="muted small">({a.sentiment.score})</span></dd>
            <dt>Emotion</dt><dd>{a.sentiment.emotion}</dd>
            <dt>Distress</dt><dd style={{ paddingTop: 6 }}><Bar value={a.sentiment.distress * 100} color="#dc2626" /></dd>
            <dt>Duration</dt><dd>{e.duration_days ? `~${e.duration_days} day(s)` : '—'}</dd>
            <dt>Landmark</dt><dd>{e.landmark || '—'}</dd>
          </dl>
          <div style={{ marginTop: 10 }}>
            {e.urgency_terms.map((t) => <span key={t} className="chip red"><AlertTriangle size={11} /> {t}</span>)}
            {e.vulnerable_groups.map((t) => <span key={t} className="chip warn"><Users size={11} /> {t}</span>)}
          </div>
        </Card>
        <Card title={<><Copy size={18} color="#2563eb" /> Duplicates & Similar</>}>
          {dup && (
            <div className="alert High" style={{ marginBottom: 10 }}>
              <b><Link2 size={14} style={{ verticalAlign: -2 }} /> Possible duplicate of {dup.id}</b>
              <p>{dup.distance_m != null
                ? `Same issue already reported ${fmtDistance(dup.distance_m)} (GPS) — linked so officers can avoid duplicate field visits.`
                : 'Same issue already reported in this ward (no GPS on one of the reports) — linked so officers can avoid duplicate field visits.'}</p>
            </div>
          )}
          {a.similar_cases?.length ? a.similar_cases.slice(0, 4).map((s) => (
            <Row {...(!compact && { to: `/grievances/${s.id}` })} key={s.id} className="row-flex between" style={{ padding: '6px 0', borderBottom: '1px solid #e9ecef', flexWrap: 'nowrap' }}>
              <span className="small" style={{ minWidth: 0 }}><span className="mono muted">{s.id}</span><br />{s.title}</span>
              <span style={{ textAlign: 'right' }}><StatusBadge status={s.status} /><br /><span className="small muted">{Math.round(s.similarity * 100)}% match{s.distance_m != null && ` · ${fmtDistance(s.distance_m)}`}</span></span>
            </Row>
          )) : <div className="muted small">No similar past cases.</div>}
        </Card>
      </div>

      <Card title={<><Lightbulb size={18} color="#16a34a" /> Recommended Resolution</>} sub="Playbook + learnt from past cases">
        <ol className="steps">{rec.action_plan.map((s, i) => <li key={i}>{s}</li>)}</ol>
        {rec.coordinate_with?.length > 0 && (
          <p className="small" style={{ marginTop: 10 }}><b>Inter-department coordination:</b> {rec.coordinate_with.join(', ')}</p>
        )}
        {rec.proven_resolutions?.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div className="small muted row-flex"><History size={13} /> What resolved similar cases before</div>
            {rec.proven_resolutions.map((p) => <span key={p.action} className="chip" style={{ background: '#e7f6ec', color: '#16a34a' }}>{p.action} ×{p.times_used}</span>)}
          </div>
        )}
      </Card>
    </div>
  )
}
