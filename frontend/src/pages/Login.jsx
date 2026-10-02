import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { KeyRound, LogIn } from 'lucide-react'
import { api, session } from '../api'
import { Card } from '../components/ui'

export default function Login({ meta }) {
  const nav = useNavigate()
  const from = useLocation().state?.from || '/'
  const [form, setForm] = useState({ username: '', password: '' })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const demo = meta?.demo_login
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setErr('')
    try { session.set(await api.login(form)); nav(from, { replace: true }) } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  return (
    <div style={{ maxWidth: 420, margin: '60px auto' }}>
      <Card title={<><KeyRound size={18} color="#2563eb" /> Officer sign in</>}>
        <p className="small muted" style={{ marginTop: 0 }}>The officer console holds complaint evidence, photos and case decisions, so it needs a login. Citizens’ names and phone numbers are never shown in it. Citizens do not need an account to <Link to="/citizen" style={{ textDecoration: 'underline' }}>raise</Link> or <Link to="/track" style={{ textDecoration: 'underline' }}>track</Link> a grievance.</p>
        <form onSubmit={submit}>
          <div className="field"><label>Username</label><input className="input" autoFocus autoComplete="username" value={form.username} onChange={set('username')} /></div>
          <div className="field"><label>Password</label><input className="input" type="password" autoComplete="current-password" value={form.password} onChange={set('password')} /></div>
          {err && <p className="small" style={{ color: '#dc2626' }}>{err}</p>}
          <button className="btn primary" style={{ width: '100%', justifyContent: 'center' }} disabled={busy || !form.username || !form.password}><LogIn size={16} /> Sign in</button>
        </form>
        {demo && (
          <div className="alert High" style={{ margin: '14px 0 0' }}>
            <b>Demo build</b>
            <p>No officer password is configured, so a demo account is active: <span className="mono">{demo.username}</span> / <span className="mono">{demo.password}</span>. Set <span className="mono">OFFICER_PASSWORD</span> on the server to remove it.</p>
            <button className="btn" type="button" style={{ marginTop: 8 }} onClick={() => setForm(demo)}>Fill demo credentials</button>
          </div>
        )}
      </Card>
    </div>
  )
}
