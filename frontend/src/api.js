const base = import.meta.env.VITE_API_URL || ''

async function req(path, opts = {}) {
  const r = await fetch(base + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
  return r.json()
}

export const api = {
  meta: () => req('/api/meta'),
  stats: () => req('/api/stats'),
  analytics: () => req('/api/analytics'),
  alerts: () => req('/api/alerts'),
  hotspots: () => req('/api/hotspots'),
  analyze: (body) => req('/api/analyze', { method: 'POST', body }),
  create: (body) => req('/api/grievances', { method: 'POST', body }),
  list: (params = {}) => req('/api/grievances?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v))),
  get: (id) => req(`/api/grievances/${encodeURIComponent(id)}`),
  update: (id, body) => req(`/api/grievances/${id}`, { method: 'PATCH', body }),
  feedback: (id, rating) => req(`/api/grievances/${id}/feedback`, { method: 'POST', body: { rating } }),
  draft: (id) => req(`/api/grievances/${id}/draft`, { method: 'POST' }),
}

export const PRIORITY_COLORS = { Critical: '#dc2626', High: '#f97316', Medium: '#eab308', Low: '#22c55e' }
export const STATUS_COLORS = { Submitted: '#64748b', Assigned: '#6366f1', 'In Progress': '#0ea5e9', Resolved: '#16a34a', Rejected: '#9ca3af' }

export function timeAgo(ts) {
  const s = (Date.now() - new Date(ts).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}
export const fmtHours = (h) => (h == null ? '—' : h < 48 ? `${Math.round(h)} h` : `${(h / 24).toFixed(1)} d`)
