import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, Mic, Send, Sparkles } from 'lucide-react'
import { api } from '../api'
import AnalysisPanel from '../components/AnalysisPanel'
import { Card } from '../components/ui'

const SAMPLES = [
  'Live electric wire has fallen near the primary school in Kothrud since yesterday. Children walk here daily, extremely dangerous!',
  'Drainage overflowing near the vegetable market in Hadapsar for 3 days, sewage entering homes and kids falling sick.',
  'Street lights not working for 2 weeks near the bus stop in Viman Nagar, women feel unsafe walking at night.',
  'Pani nahi aa raha in our society in Wakad for 4 days, elderly people suffering. Complaint given twice but still ignored.',
  'Hawkers have occupied the entire footpath near the station in Swargate.',
]

export default function Submit({ meta }) {
  const [form, setForm] = useState({ text: '', ward: '', citizen_name: '', phone: '', channel: 'Web' })
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [created, setCreated] = useState(null)
  const [listening, setListening] = useState(false)
  const timer = useRef()

  useEffect(() => {
    clearTimeout(timer.current)
    if (form.text.trim().length < 15) { setAnalysis(null); return }
    timer.current = setTimeout(() => {
      setLoading(true)
      api.analyze({ text: form.text, ward: form.ward || null }).then(setAnalysis).finally(() => setLoading(false))
    }, 500)
  }, [form.text, form.ward])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async () => {
    setLoading(true)
    try { setCreated(await api.create({ ...form, ward: form.ward || null })) } finally { setLoading(false) }
  }
  const voice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { setListening(false); return }
    const r = new SR(); r.lang = 'en-IN'; r.interimResults = false
    r.onresult = (e) => setForm((f) => ({ ...f, text: (f.text + ' ' + e.results[0][0].transcript).trim() }))
    r.onend = () => setListening(false)
    setListening(true); r.start()
  }

  if (created) return (
    <div style={{ maxWidth: 720, margin: '40px auto' }}>
      <Card>
        <div style={{ textAlign: 'center', padding: '10px 0 6px' }}>
          <CheckCircle2 size={56} color="#16a34a" />
          <h2 style={{ margin: '10px 0 4px' }}>Grievance registered</h2>
          <p className="muted">Your tracking ID</p>
          <div className="mono" style={{ fontSize: 26, fontWeight: 700, letterSpacing: 1 }}>{created.id}</div>
          <p>Routed to <b>{created.department}</b> · Priority <b>{created.priority_level}</b></p>
          <div className="row-flex" style={{ justifyContent: 'center' }}>
            <Link className="btn primary" to={`/track/${created.id}`}>Track status</Link>
            <Link className="btn" to={`/grievances/${created.id}`}>Open in officer console</Link>
            <button className="btn" onClick={() => { setCreated(null); setForm({ ...form, text: '' }) }}>Raise another</button>
          </div>
        </div>
      </Card>
    </div>
  )

  return (
    <>
      <div className="hero">
        <h2>Raise a grievance</h2>
        <p>Describe the problem in your own words — English, Hindi or Hinglish. Our AI instantly identifies the department, urgency and the fastest way to resolve it.</p>
      </div>
      <div className="grid g2" style={{ alignItems: 'start' }}>
        <Card title="Complaint details">
          <div className="field">
            <label>Describe the issue *</label>
            <textarea className="input" value={form.text} onChange={set('text')} placeholder="e.g. Garbage not collected near the park in Baner for 5 days, very bad smell…" />
            <div className="row-flex between">
              <span className="small muted">{form.text.length} chars · include location & how long</span>
              <button className="btn" onClick={voice} type="button"><Mic size={15} color={listening ? '#dc2626' : undefined} />{listening ? 'Listening…' : 'Speak'}</button>
            </div>
          </div>
          <div className="samples small"><div className="muted" style={{ marginBottom: 6 }}>Try a sample:</div>
            {SAMPLES.map((s, i) => <button key={i} onClick={() => setForm({ ...form, text: s })}>{s.slice(0, 38)}…</button>)}
          </div>
          <div className="grid g2" style={{ marginTop: 12 }}>
            <div className="field"><label>Ward / Area</label>
              <select className="input" value={form.ward} onChange={set('ward')}>
                <option value="">Auto-detect from text</option>
                {meta?.wards.map((w) => <option key={w}>{w}</option>)}
              </select>
            </div>
            <div className="field"><label>Channel</label>
              <select className="input" value={form.channel} onChange={set('channel')}>
                {['Web', 'Mobile App', 'WhatsApp', 'Call Centre', 'Twitter/X'].map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="field"><label>Your name</label><input className="input" value={form.citizen_name} onChange={set('citizen_name')} /></div>
            <div className="field"><label>Mobile</label><input className="input" value={form.phone} onChange={set('phone')} /></div>
          </div>
          <button className="btn saffron" style={{ width: '100%', justifyContent: 'center', padding: 12 }} disabled={form.text.trim().length < 10 || loading} onClick={submit}>
            <Send size={16} /> Submit grievance
          </button>
        </Card>
        <div>
          {!analysis && (
            <Card>
              <div className="empty"><Sparkles size={36} color="#a5b4fc" /><p>Start typing — live AI analysis appears here.</p></div>
            </Card>
          )}
          {analysis && <div className={loading ? 'pulse' : ''}><AnalysisPanel a={analysis} compact /></div>}
        </div>
      </div>
    </>
  )
}
