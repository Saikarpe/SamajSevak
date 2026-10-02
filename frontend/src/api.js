export const API_BASE = import.meta.env.VITE_API_URL || ''

// officer session: token from /api/auth/login, kept for the browser tab group
export const session = {
  get: () => { try { return JSON.parse(localStorage.getItem('officer')) } catch { return null } },
  set: (s) => { s ? localStorage.setItem('officer', JSON.stringify(s)) : localStorage.removeItem('officer'); window.dispatchEvent(new Event('officer')) },
}

// citizen session (name + mobile). Sent in its own header so a demo browser can hold both sessions.
export const citizen = {
  get: () => { try { return JSON.parse(localStorage.getItem('citizen')) } catch { return null } },
  set: (s) => { s ? localStorage.setItem('citizen', JSON.stringify(s)) : localStorage.removeItem('citizen'); window.dispatchEvent(new Event('citizen')) },
}

async function call(path, opts = {}) {
  const token = session.get()?.token
  const me = citizen.get()?.token
  const r = await fetch(API_BASE + path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }), ...(me && { 'X-Citizen-Token': me }) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (r.status === 401 && token && !path.startsWith('/api/citizen')) session.set(null) // expired: back to the login page
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
  return r
}
const req = (path, opts) => call(path, opts).then((r) => r.json())

export const api = {
  meta: () => req('/api/meta'),
  login: (body) => req('/api/auth/login', { method: 'POST', body }),
  stats: () => req('/api/stats'),
  analytics: () => req('/api/analytics'),
  alerts: () => req('/api/alerts'),
  hotspots: () => req('/api/hotspots'),
  analyze: (body) => req('/api/analyze', { method: 'POST', body }),
  create: (body) => req('/api/grievances', { method: 'POST', body }),
  track: (id) => req(`/api/track/${encodeURIComponent(id)}`),
  citizenLogin: (body) => req('/api/citizen/login', { method: 'POST', body }).then((c) => { citizen.set(c); return c }),
  mine: () => req('/api/citizen/grievances'),
  publicStats: () => req('/api/public/stats'),
  list: (params = {}) => req('/api/grievances?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v))),
  get: (id) => req(`/api/grievances/${encodeURIComponent(id)}`),
  // the evidence photo needs the officer token, so it is fetched and shown from a blob URL
  photo: (id) => call(`/api/grievances/${encodeURIComponent(id)}/photo`).then((r) => r.blob()).then(URL.createObjectURL),
  update: (id, body) => req(`/api/grievances/${id}`, { method: 'PATCH', body }),
  feedback: (id, body) => req(`/api/grievances/${id}/feedback`, { method: 'POST', body }),
  draft: (id) => req(`/api/grievances/${id}/draft`, { method: 'POST' }),
  model: () => req('/api/model'),
  retrain: () => req('/api/model/retrain', { method: 'POST' }),
}

export const PRIORITY_COLORS = { Critical: '#dc2626', High: '#ea580c', Medium: '#d97706', Low: '#5c6773' }
export const STATUS_COLORS = { Submitted: '#5c6773', Assigned: '#4f46e5', 'In Progress': '#0284c7', Resolved: '#0d9488', 'Not Satisfied': '#dc2626', Closed: '#16a34a', Rejected: '#8a949e' }
// escalation ladder: Complaint and Warning are department-level, the strikes go upward
export const STAGE_COLORS = { Complaint: '#5c6773', Warning: '#d97706', 'Strike 1': '#ea580c', 'Strike 2': '#dc2626', 'Strike 3': '#991b1b' }
export const isOpen = (status) => !['Resolved', 'Closed', 'Rejected'].includes(status)

export function timeAgo(ts) {
  const s = (Date.now() - new Date(ts).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
export const fmtHours = (h) => (h == null ? '—' : h < 48 ? `${Math.round(h)} h` : `${(h / 24).toFixed(1)} d`)
export const fmtDistance = (m) => (m == null ? null : m < 1000 ? `${m} m away` : `${(m / 1000).toFixed(1)} km away`)

// Shrink a camera photo in the browser (max 1280 px, JPEG) so uploads stay small on mobile data
export async function shrinkPhoto(file, max = 1280) {
  const img = await createImageBitmap(file)
  const scale = Math.min(1, max / Math.max(img.width, img.height))
  const canvas = Object.assign(document.createElement('canvas'), { width: Math.round(img.width * scale), height: Math.round(img.height * scale) })
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/jpeg', 0.8)
}
