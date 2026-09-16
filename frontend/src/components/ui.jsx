import { PRIORITY_COLORS, STATUS_COLORS } from '../api'

export const Card = ({ title, sub, right, children, className = '', style }) => (
  <div className={`card ${className}`} style={style}>
    {(title || right) && <h3><span className="row-flex">{title}{sub && <span className="sub">{sub}</span>}</span>{right}</h3>}
    {children}
  </div>
)

export const Stat = ({ icon: Icon, label, value, color = '#4f46e5', hint }) => (
  <div className="card stat">
    <div className="stat-icon" style={{ background: color + '1a', color }}><Icon size={22} /></div>
    <div><div className="v">{value}</div><div className="l">{label}</div>{hint && <div className="small muted">{hint}</div>}</div>
  </div>
)

export const PriorityBadge = ({ level }) => {
  const c = PRIORITY_COLORS[level] || '#64748b'
  return <span className="badge" style={{ background: c + '1f', color: c }}>● {level}</span>
}
export const StatusBadge = ({ status }) => {
  const c = STATUS_COLORS[status] || '#64748b'
  return <span className="badge" style={{ background: c + '1a', color: c }}>{status}</span>
}

export const ScoreRing = ({ score, level }) => {
  const c = PRIORITY_COLORS[level] || '#6366f1'
  return (
    <div className="score-ring" style={{ background: `conic-gradient(${c} ${score * 3.6}deg, #eef2f7 0)` }}>
      <div><div><b style={{ color: c }}>{Math.round(score)}</b><div className="small muted">/100</div></div></div>
    </div>
  )
}

export const Bar = ({ value, max = 100, color = '#6366f1' }) => (
  <div className="bar"><span style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color }} /></div>
)
