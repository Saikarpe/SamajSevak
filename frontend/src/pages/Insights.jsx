import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip as LTooltip } from 'react-leaflet'
import { Bar as RBar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, fmtHours, PRIORITY_COLORS } from '../api'
import { Bar, Card } from '../components/ui'

const SENT = { Negative: '#ef4444', Neutral: '#94a3b8', Positive: '#22c55e' }

export default function Insights() {
  const [hs, setHs] = useState(null)
  const [an, setAn] = useState(null)
  useEffect(() => { api.hotspots().then(setHs); api.analytics().then(setAn) }, [])
  if (!hs || !an) return <div className="empty pulse">Loading insights…</div>
  const maxOpen = Math.max(...hs.wards.map((w) => w.open), 1)
  return (
    <>
      <div className="page-head"><div><h2>Hotspots & Insights</h2><p>Where problems cluster, which departments lag, and how citizens feel.</p></div></div>
      <div className="grid g-main" style={{ marginBottom: 16 }}>
        <Card title="Live grievance hotspot map" sub="Open cases · bubble = ward load">
          <MapContainer center={[18.53, 73.85]} zoom={12} scrollWheelZoom={false}>
            <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {hs.wards.map((w) => (
              <CircleMarker key={w.ward} center={[w.lat, w.lng]} radius={10 + 22 * (w.open / maxOpen)}
                pathOptions={{ color: w.critical / w.open > 0.4 ? '#dc2626' : '#f97316', fillOpacity: 0.25, weight: 1.5 }}>
                <LTooltip><b>{w.ward}</b><br />{w.open} open · {w.critical} high/critical<br />Top issue: {w.top_category} ({w.top_count})</LTooltip>
              </CircleMarker>
            ))}
            {hs.points.map((p) => (
              <CircleMarker key={p.id} center={[p.lat, p.lng]} radius={3.5} pathOptions={{ color: PRIORITY_COLORS[p.priority], fillOpacity: 0.9, weight: 0 }}>
                <LTooltip>{p.id}: {p.title}</LTooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </Card>
        <Card title="Ward risk ranking">
          <div style={{ maxHeight: 380, overflowY: 'auto' }}>
            {hs.wards.map((w) => (
              <div key={w.ward} style={{ padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                <div className="row-flex between"><b style={{ fontSize: 14 }}>{w.ward}</b><span className="small">{w.open} open · <span style={{ color: '#dc2626' }}>{w.critical} urgent</span></span></div>
                <Bar value={w.open} max={maxOpen} color={w.critical / w.open > 0.4 ? '#dc2626' : '#f97316'} />
                <div className="small muted" style={{ marginTop: 3 }}>Top issue: {w.top_category}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className="grid g-main" style={{ marginBottom: 16 }}>
        <Card title="Department performance" sub="Sorted by SLA compliance (lowest first)">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Department</th><th>Total</th><th>Open</th><th>Avg time</th><th style={{ width: 170 }}>SLA compliance</th></tr></thead>
              <tbody>
                {an.departments.map((d) => (
                  <tr key={d.department}>
                    <td style={{ fontWeight: 500 }}>{d.department}</td><td>{d.total}</td><td>{d.open}</td><td>{fmtHours(d.avg_hours)}</td>
                    <td><div className="row-flex" style={{ flexWrap: 'nowrap' }}><div style={{ flex: 1 }}><Bar value={d.sla_compliance} color={d.sla_compliance < 70 ? '#dc2626' : d.sla_compliance < 85 ? '#f59e0b' : '#16a34a'} /></div><b className="small">{d.sla_compliance}%</b></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card title="Citizen sentiment">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart margin={{ top: 20, bottom: 10 }}>
              <Pie data={an.by_sentiment} dataKey="value" nameKey="name" outerRadius={70} label={({ name, percent }) => `${name} ${Math.round(percent * 100)}%`}>
                {an.by_sentiment.map((s) => <Cell key={s.name} fill={SENT[s.name]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <p className="small muted">Negative-sentiment cases get a distress boost in the priority score so frustrated citizens are not left waiting.</p>
        </Card>
      </div>
      <Card title="Grievance volume by ward">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={an.by_ward}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} width={30} />
            <Tooltip />
            <RBar dataKey="value" name="Grievances" fill="#f97316" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </>
  )
}
