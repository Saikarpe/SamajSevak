import { PRIORITY_COLORS, STAGE_COLORS, STATUS_COLORS } from '../api'

export const Card = ({ title, sub, right, children, className = '', style }) => (
  <div className={`card ${className}`} style={style}>
    {(title || right) && <h3><span className="row-flex">{title}{sub && <span className="sub">{sub}</span>}</span>{right}</h3>}
    {children}
  </div>
)

export const Stat = ({ icon: Icon, label, value, color = '#2563eb', hint }) => (
  <div className="card stat">
    <div className="stat-icon" style={{ background: color + '1a', color }}><Icon size={22} /></div>
    <div><div className="v">{value}</div><div className="l">{label}</div>{hint && <div className="small muted">{hint}</div>}</div>
  </div>
)

// `label` overrides the displayed text (translated citizen pages); colour still follows level / status
export const PriorityBadge = ({ level, label }) => {
  const c = PRIORITY_COLORS[level] || '#5c6773'
  return <span className="badge" style={{ background: c + '1a', color: c }}>{label || level}</span>
}
export const StatusBadge = ({ status, label }) => {
  const c = STATUS_COLORS[status] || '#5c6773'
  return <span className="badge" style={{ background: c + '1a', color: c }}>{label || status}</span>
}

export const StageBadge = ({ stage, label }) => {
  const c = STAGE_COLORS[stage] || '#5c6773'
  return <span className="badge" style={{ background: c + '1a', color: c }}>{label || stage}</span>
}

// The five escalation stages in order, with the current one highlighted
export const StageLadder = ({ stages, current, labels = {} }) => {
  const at = stages.indexOf(current)
  return (
    <div className="row-flex" style={{ gap: 0, flexWrap: 'nowrap' }}>
      {stages.map((s, i) => (
        <div key={s} style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ height: 6, background: i <= at ? STAGE_COLORS[current] : '#e9ecef', borderRadius: 4, margin: '0 3px' }} />
          <div className="small" style={{ marginTop: 6, fontWeight: i === at ? 700 : 400, color: i <= at ? '#1b2430' : '#8a949e' }}>{labels[s] || s}</div>
        </div>
      ))}
    </div>
  )
}

export const ScoreRing = ({ score, level }) => {
  const c = PRIORITY_COLORS[level] || '#2563eb'
  return (
    <div className="score-ring" style={{ background: `conic-gradient(${c} ${score * 3.6}deg, #e9ecef 0)` }}>
      <div><div><b style={{ color: c }}>{Math.round(score)}</b><div className="small muted">/100</div></div></div>
    </div>
  )
}

export const Bar = ({ value, max = 100, color = '#2563eb' }) => (
  <div className="bar"><span style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color }} /></div>
)
