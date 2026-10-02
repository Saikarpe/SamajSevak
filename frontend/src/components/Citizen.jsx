import { useEffect, useState } from 'react'
import { LogIn, LogOut, UserRound } from 'lucide-react'
import { api, citizen } from '../api'

// the signed-in citizen ({ id, name, token }) or null; follows sign-in / sign-out in any tab
export function useCitizen() {
  const [me, setMe] = useState(citizen.get)
  useEffect(() => {
    const sync = () => setMe(citizen.get())
    window.addEventListener('citizen', sync); window.addEventListener('storage', sync)
    return () => { window.removeEventListener('citizen', sync); window.removeEventListener('storage', sync) }
  }, [])
  return me
}

// Name + mobile number is the whole login. t = translated strings from i18n.
export function CitizenLogin({ t, me }) {
  const [form, setForm] = useState({ name: '', phone: '' })
  const [err, setErr] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  if (me) return (
    <div className="row-flex small">
      <UserRound size={14} /> {t.signedIn} <b>{me.name}</b>
      <button className="btn" type="button" onClick={() => citizen.set(null)}><LogOut size={14} /> {t.signOut}</button>
    </div>
  )
  const submit = (e) => { e.preventDefault(); setErr(''); api.citizenLogin(form).catch((x) => setErr(x.message)) }
  return (
    <form onSubmit={submit}>
      <div className="row-flex" style={{ alignItems: 'flex-end' }}>
        <div className="field" style={{ flex: 1, minWidth: 150, marginBottom: 0 }}><label>{t.name}</label><input className="input" value={form.name} onChange={set('name')} autoComplete="name" /></div>
        <div className="field" style={{ flex: 1, minWidth: 150, marginBottom: 0 }}><label>{t.mobile}</label><input className="input" value={form.phone} onChange={set('phone')} inputMode="numeric" autoComplete="tel" /></div>
        <button className="btn primary" disabled={!form.name || !form.phone}><LogIn size={15} /> {t.signIn}</button>
      </div>
      {err && <p className="small" style={{ color: '#dc2626', marginBottom: 0 }}>{err}</p>}
    </form>
  )
}
