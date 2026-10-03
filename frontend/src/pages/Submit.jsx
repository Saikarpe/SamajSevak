import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { CircleMarker, MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { Camera, CheckCircle2, ImageIcon, LocateFixed, MapPin, Mic, Send, Sparkles, Users, X } from 'lucide-react'
import { api, citizen, fmtDistance, shrinkPhoto } from '../api'
import AnalysisPanel from '../components/AnalysisPanel'
import LiveCamera, { liveCameraAvailable } from '../components/LiveCamera'
import { useCitizen } from '../components/Citizen'
import { Card, StatusBadge } from '../components/ui'
import { LANGS, LangSwitch, useLang } from '../i18n'

const PUNE = [18.53, 73.85]
const VOICE_ERRORS = {
  unsupported: 'Voice input is not supported in this browser. Use Chrome or Edge, or type the complaint.',
  'not-allowed': 'Microphone access is blocked. Click the lock icon in the address bar, allow the microphone, then try again.',
  'service-not-allowed': 'This browser has speech recognition turned off. Try Chrome or Edge.',
  'audio-capture': 'No microphone was found. Connect one and try again.',
  network: 'Voice input needs an internet connection: the browser sends audio to its speech service.',
  'no-speech': 'No speech was heard. Check the microphone is not muted and try again.',
  'language-not-supported': 'This browser cannot recognise speech in the selected language. Switch language or type the complaint.',
  busy: 'Voice input is already running.',
}

// tap to drop a pin; follows the GPS fix or the chosen ward
function PinPicker({ point, center, onPick }) {
  const map = useMap()
  useMapEvents({ click: (e) => onPick({ lat: e.latlng.lat, lng: e.latlng.lng, geo_source: 'pin' }) })
  useEffect(() => { map.setView(center, point ? 16 : 13) }, [center[0], center[1]])
  return point ? <CircleMarker center={[point.lat, point.lng]} radius={9} pathOptions={{ color: '#dc2626', fillOpacity: 0.6 }} /> : null
}

export default function Submit({ meta }) {
  const [lang, t, setLang] = useLang()
  const me = useCitizen()
  const [form, setForm] = useState({ text: '', ward: '', citizen_name: '', phone: '', channel: 'Web', citizen_category: '' })
  const [point, setPoint] = useState(null) // { lat, lng, geo_source: 'gps' | 'pin' }
  const [locating, setLocating] = useState(false)
  const [photo, setPhoto] = useState(null)
  const [live, setLive] = useState(false) // photo came from the camera, not the gallery
  const [camera, setCamera] = useState(false) // live viewfinder open
  const [picker, setPicker] = useState(false) // 'Add a photo' choice: camera or gallery
  const gallery = useRef(null)
  const nativeCam = useRef(null) // phone's own camera app: used when the browser blocks the live camera (plain http)
  const [analysis, setAnalysis] = useState(null)
  const [joinId, setJoinId] = useState(null) // existing issue the citizen chose to join
  const [loading, setLoading] = useState(false)
  const [created, setCreated] = useState(null)
  const [listening, setListening] = useState(false)
  const [err, setErr] = useState('')
  const [voiceErr, setVoiceErr] = useState('')
  const timer = useRef()
  const recog = useRef(null) // the running SpeechRecognition, if any

  useEffect(() => {
    clearTimeout(timer.current)
    if (form.text.trim().length < 15) { setAnalysis(null); return }
    timer.current = setTimeout(() => {
      setLoading(true)
      api.analyze({ text: form.text, ward: form.ward || null, lat: point?.lat, lng: point?.lng, citizen_category: form.citizen_category || null })
        .then(setAnalysis).finally(() => setLoading(false))
    }, 500)
  }, [form.text, form.ward, form.citizen_category, point])

  const issues = analysis?.existing_issues || []
  const joining = issues.find((i) => i.id === joinId)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async () => {
    setLoading(true); setErr('')
    try {
      // name + mobile on the form is the citizen's account: sign in (or register) before filing
      if (!citizen.get() && form.citizen_name && form.phone) await api.citizenLogin({ name: form.citizen_name, phone: form.phone })
      const { citizen_name, phone, ...rest } = form
      setCreated(await api.create({
        ...rest, ward: form.ward || null, citizen_category: form.citizen_category || null, ...point, photo,
        join_issue: joining?.id || null, shown_issues: joining ? [] : issues.map((i) => i.id),
      }))
    } catch (e) { setErr(e.message) } finally { setLoading(false) }
  }
  // Browser speech recognition (Chrome / Edge; audio is transcribed by the browser's online service).
  // Click once to start, again to stop. Every failure is shown instead of failing silently.
  const voice = () => {
    if (recog.current) { recog.current.stop(); return }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { setVoiceErr(VOICE_ERRORS.unsupported); return }
    const r = new SR()
    r.lang = LANGS[lang].speech; r.continuous = true; r.interimResults = true
    const before = form.text.trim()
    r.onresult = (e) => {
      const said = Array.from(e.results).map((x) => x[0].transcript).join(' ')
      setForm((f) => ({ ...f, text: (before + ' ' + said).trim() }))
    }
    r.onerror = (e) => { if (e.error !== 'aborted') setVoiceErr(VOICE_ERRORS[e.error] || `Voice input failed (${e.error}).`) }
    r.onend = () => { recog.current = null; setListening(false) }
    setVoiceErr('')
    try { r.start(); recog.current = r; setListening(true) } catch { setVoiceErr(VOICE_ERRORS.busy) }
  }
  const locate = () => {
    setLocating(true); setErr('')
    navigator.geolocation.getCurrentPosition(
      (p) => { setPoint({ lat: p.coords.latitude, lng: p.coords.longitude, geo_source: 'gps' }); setLocating(false) },
      () => { setErr(t.gpsFail); setLocating(false) },
      { enableHighAccuracy: true, timeout: 10000 })
  }
  const pickPhoto = async (e) => {
    const file = e.target.files[0]
    e.target.value = ''
    if (file) try { setPhoto(await shrinkPhoto(file)); setLive(e.target === nativeCam.current) } catch { setErr('Could not read this image.') }
  }
  // 'Open camera': the live viewfinder where the browser allows it, otherwise the phone's camera app (same tap)
  const openCamera = () => { setPicker(false); if (liveCameraAvailable()) setCamera(true); else nativeCam.current?.click() }
  const reset = () => { setCreated(null); setPhoto(null); setLive(false); setPoint(null); setJoinId(null); setForm({ ...form, text: '' }) }
  const center = point ? [point.lat, point.lng] : meta?.ward_centers?.[form.ward] || PUNE

  if (created) return (
    <div style={{ maxWidth: 720, margin: '40px auto' }}>
      <Card>
        <div style={{ textAlign: 'center', padding: '10px 0 6px' }}>
          <CheckCircle2 size={56} color="#16a34a" />
          <h2 style={{ margin: '10px 0 4px' }}>{t.registered}</h2>
          <p className="muted">{t.yourId}</p>
          <div className="mono" style={{ fontSize: 26, fontWeight: 700, letterSpacing: 1 }}>{created.id}</div>
          {created.master_id !== created.id && (
            <p className="issue-card joined" style={{ display: 'inline-block', marginTop: 12 }}>
              <Users size={14} style={{ verticalAlign: -2 }} /> {created.association_source === 'CITIZEN' ? t.joinedDone : t.aiLinked} <b className="mono">{created.master_id}</b> · {created.report_count} {t.reports}
            </p>
          )}
          <p>{t.routed} <b>{created.department}</b> · {t.priority} <b>{t.level[created.priority_level] || created.priority_level}</b></p>
          <div className="row-flex" style={{ justifyContent: 'center' }}>
            <Link className="btn primary" to={`/track/${created.id}`}>{t.track}</Link>
            {me && <Link className="btn" to="/my">{t.my}</Link>}
            <button className="btn" onClick={reset}>{t.another}</button>
          </div>
        </div>
      </Card>
    </div>
  )

  return (
    <>
      <div className="hero">
        <div className="row-flex between" style={{ alignItems: 'flex-start', position: 'relative', zIndex: 1 }}>
          <div><h2>{t.heroTitle}</h2><p>{t.heroText}</p></div>
          <LangSwitch lang={lang} onChange={setLang} />
        </div>
      </div>
      <div className="grid g2" style={{ alignItems: 'start' }}>
        <Card title={t.details}>
          <div className="field">
            <label>{t.photo}</label>
            <div className="row-flex">
              <button className="btn" type="button" onClick={() => setPicker(true)}><Camera size={15} />{t.addPhoto}</button>
              <input ref={gallery} type="file" accept="image/*" hidden onChange={pickPhoto} />
              <input ref={nativeCam} type="file" accept="image/*" capture="environment" hidden onChange={pickPhoto} />
              {photo && <><img src={photo} alt="" className="thumb" />{live && <span className="chip" style={{ background: '#e7f6ec', color: '#16a34a' }}>{t.livePhoto}</span>}<button className="btn" type="button" onClick={() => { setPhoto(null); setLive(false) }}><X size={14} />{t.remove}</button></>}
              {!photo && <span className="small muted">{t.photoHint}</span>}
            </div>
          </div>
          <div className="field">
            <label>{t.describe}</label>
            <textarea className="input" value={form.text} onChange={set('text')} placeholder={t.placeholder} />
            <div className="row-flex between">
              <span className="small muted">{form.text.length} {t.hint}</span>
              <button className="btn" onClick={voice} type="button"><Mic size={15} color={listening ? '#dc2626' : undefined} />{listening ? t.listening : `${t.speak} (${LANGS[lang].label})`}</button>
            </div>
            {voiceErr && <span className="small" style={{ color: '#dc2626' }}>{voiceErr}</span>}
          </div>
          <div className="samples small"><div className="muted" style={{ marginBottom: 6 }}>{t.trySample}</div>
            {t.samples.map((s, i) => <button key={i} onClick={() => setForm({ ...form, text: s })}>{s.slice(0, 38)}…</button>)}
          </div>
          <div className="field" style={{ marginTop: 12 }}>
            <label>{t.location}</label>
            <div className="row-flex">
              <button className="btn" type="button" onClick={locate} disabled={locating || !navigator.geolocation}><LocateFixed size={15} />{locating ? t.locating : t.useGps}</button>
              {point && <span className="chip" style={{ background: '#e7f6ec', color: '#16a34a' }}><MapPin size={11} /> {point.geo_source === 'gps' ? t.gpsOk : t.pinOk} · {point.lat.toFixed(4)}, {point.lng.toFixed(4)}</span>}
              {point && <button className="btn" type="button" onClick={() => setPoint(null)}><X size={14} />{t.clear}</button>}
            </div>
            <MapContainer center={PUNE} zoom={13} style={{ height: 200 }}>
              <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <PinPicker point={point} center={center} onPick={setPoint} />
            </MapContainer>
            <span className="small muted">{t.pinHint}</span>
          </div>
          <div className="grid g3">
            <div className="field"><label>{t.category}</label>
              <select className="input" value={form.citizen_category} onChange={set('citizen_category')}>
                <option value="">{t.aiDecide}</option>
                {Object.keys(meta?.categories || {}).map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="field"><label>{t.ward}</label>
              <select className="input" value={form.ward} onChange={set('ward')}>
                <option value="">{t.autoDetect}</option>
                {meta?.wards.map((w) => <option key={w}>{w}</option>)}
              </select>
            </div>
            <div className="field"><label>{t.channel}</label>
              <select className="input" value={form.channel} onChange={set('channel')}>
                {['Web', 'Mobile App', 'WhatsApp', 'Call Centre', 'Twitter/X'].map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label>{t.account}</label>
            {me ? (
              <div className="row-flex small">{t.signedIn} <b>{me.name}</b><button className="btn" type="button" onClick={() => citizen.set(null)}>{t.signOut}</button></div>
            ) : (
              <div className="grid g2">
                <input className="input" placeholder={t.name} value={form.citizen_name} onChange={set('citizen_name')} autoComplete="name" />
                <input className="input" placeholder={t.mobile} value={form.phone} onChange={set('phone')} inputMode="numeric" autoComplete="tel" />
              </div>
            )}
            <span className="small muted">{t.accountHint}</span>
          </div>
          {picker && (
            <div className="sheet-backdrop" onClick={() => setPicker(false)}>
              <div className="sheet" onClick={(e) => e.stopPropagation()}>
                <b className="sheet-title">{t.addPhoto}</b>
                <button type="button" className="sheet-option" onClick={openCamera}><Camera size={20} />{t.openCamera}</button>
                <button type="button" className="sheet-option" onClick={() => { setPicker(false); gallery.current?.click() }}><ImageIcon size={20} />{t.fromGallery}</button>
                <button type="button" className="sheet-option cancel" onClick={() => setPicker(false)}>{t.cancel}</button>
              </div>
            </div>
          )}
          {camera && (
            <LiveCamera t={t} point={point}
              onCapture={(p) => { setPhoto(p); setLive(true); setCamera(false) }}
              onClose={() => setCamera(false)}
              onFallback={() => { setCamera(false); nativeCam.current?.click() }} />
          )}
          {err && <p className="small" style={{ color: '#dc2626' }}>{err}</p>}
          <button className="btn saffron" style={{ width: '100%', justifyContent: 'center', padding: 12 }} disabled={form.text.trim().length < 10 || loading} onClick={submit}>
            <Send size={16} /> {joining ? `${t.join} ${joining.id}` : t.submit}
          </button>
        </Card>
        <div>
          {!analysis && (
            <Card>
              <div className="empty"><Sparkles size={36} color="#9aa5b1" /><p>{t.startTyping}</p></div>
            </Card>
          )}
          {issues.length > 0 && (
            <Card title={<><Users size={18} color="#2563eb" /> {t.existingTitle}</>} style={{ marginBottom: 16 }}>
              <p className="small muted" style={{ marginTop: 0 }}>{t.existingText}</p>
              {issues.map((i) => (
                <div key={i.id} className={`issue-card ${joinId === i.id ? 'joined' : ''}`}>
                  <div className="row-flex between">
                    <span className="mono">{i.id}</span>
                    <span><StatusBadge status={i.status} label={t.status[i.status]} /></span>
                  </div>
                  <b style={{ fontSize: 14 }}>{i.title}</b>
                  <div className="small muted">{i.category} · {i.ward}{i.distance_m != null && ` · ${fmtDistance(i.distance_m)}`} · {i.report_count} {t.reports}</div>
                  <div className="row-flex" style={{ marginTop: 8 }}>
                    {joinId === i.id
                      ? <><b className="small" style={{ color: '#16a34a' }}>{t.joining}</b><button className="btn" onClick={() => setJoinId(null)}>{t.different}</button></>
                      : <button className="btn primary" onClick={() => setJoinId(i.id)}>{t.join}</button>}
                  </div>
                </div>
              ))}
            </Card>
          )}
          {analysis && <div className={loading ? 'pulse' : ''}><AnalysisPanel a={analysis} compact /></div>}
        </div>
      </div>
    </>
  )
}
