import { ArrowRight, Brain, Copy, FileSearch, Gauge, Languages, Lightbulb, MessageSquareText, Radar, Tags } from 'lucide-react'
import { Card } from '../components/ui'

const STAGES = [
  { icon: Languages, t: 'Ingest & Clean', d: 'Multi-channel text (web, app, WhatsApp, call-centre transcripts). Strips greetings/boilerplate; supports Hinglish.' },
  { icon: Tags, t: 'Classify & Route', d: 'TF-IDF word + char n-gram features → Logistic Regression over 11 categories; maps to department & SLA. Low confidence → human triage.' },
  { icon: FileSearch, t: 'Extract Entities', d: 'Ward, landmark, issue duration, risk keywords and vulnerable groups (children, elderly, patients…).' },
  { icon: MessageSquareText, t: 'Sentiment & Distress', d: 'Lexicon-based sentiment with intensifiers, exclamation & caps signals → emotion and distress score.' },
  { icon: Copy, t: 'Duplicate Detection', d: 'Cosine similarity on TF-IDF vectors, category-aware re-ranking, same-ward filter → merge suggestions.' },
  { icon: Gauge, t: 'Explainable Priority', d: 'Transparent 0–100 score: severity + risk + vulnerability + distress + duration + cluster size + repeat complaint.' },
  { icon: Lightbulb, t: 'Recommend Resolution', d: 'Context-ranked SOP playbook + proven actions retrieved from similar resolved cases + ETA from historical resolution times.' },
  { icon: Radar, t: 'Detect Emerging Issues', d: 'Ward × category spike detection vs 3-week baseline → systemic root-cause alerts and SLA-breach escalation.' },
  { icon: Brain, t: 'GenAI Assist (optional)', d: 'Gemini / OpenAI drafts empathetic citizen replies grounded in the ML analysis; template fallback keeps it working offline.' },
]

export default function AILab({ meta }) {
  const m = meta?.model_metrics || {}
  return (
    <>
      <div className="page-head"><div><h2>AI Engine</h2><p>How SamajSevak turns raw complaints into prioritised, actionable decisions.</p></div></div>
      <div className="grid g3" style={{ marginBottom: 16 }}>
        {STAGES.map((s, i) => (
          <Card key={s.t}>
            <div className="row-flex" style={{ marginBottom: 6 }}>
              <div className="stat-icon" style={{ background: '#eef2ff', color: '#4f46e5', width: 36, height: 36 }}><s.icon size={18} /></div>
              <b>{i + 1}. {s.t}</b>{i < STAGES.length - 1 && <ArrowRight size={14} className="muted" style={{ marginLeft: 'auto' }} />}
            </div>
            <div className="small muted" style={{ lineHeight: 1.55 }}>{s.d}</div>
          </Card>
        ))}
      </div>
      <div className="grid g2">
        <Card title="Classifier evaluation">
          <dl className="kv">
            <dt>Training samples</dt><dd>{m.train_size ?? '—'} (+{m.test_size ?? '—'} test)</dd>
            <dt>Categories</dt><dd>{m.classes?.length ?? '—'}</dd>
            <dt>Test accuracy</dt><dd>{m.test_accuracy != null ? `${(m.test_accuracy * 100).toFixed(1)}%` : '—'} <span className="small muted">(synthetic split)</span></dd>
            <dt>Macro F1</dt><dd>{m.test_macro_f1 ?? '—'}</dd>
            <dt>Hand-written holdout</dt><dd>{m.holdout_accuracy != null ? `${(m.holdout_accuracy * 100).toFixed(1)}% on ${m.holdout_size} unseen complaints` : '—'}</dd>
          </dl>
          <p className="small muted">The synthetic split is easy by design; the hand-written holdout is the realistic check. In production the model retrains on officer-corrected labels (human-in-the-loop).</p>
        </Card>
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
