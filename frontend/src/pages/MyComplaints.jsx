import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { CitizenLogin, useCitizen } from '../components/Citizen'
import { Card, StageBadge, StatusBadge } from '../components/ui'
import { LangSwitch, useLang } from '../i18n'

// A citizen's own reports only; every row is the public tracking view of that report
export default function MyComplaints() {
  const [lang, t, setLang] = useLang()
  const me = useCitizen()
  const [rows, setRows] = useState(null)
  useEffect(() => { setRows(null); if (me) api.mine().then(setRows).catch(() => setRows([])) }, [me?.id])
  return (
    <div style={{ maxWidth: 820, margin: '0 auto' }}>
      <div className="page-head"><div><h2>{t.my}</h2><p>{t.myHint}</p></div><LangSwitch lang={lang} onChange={setLang} /></div>
      <Card><CitizenLogin t={t} me={me} /></Card>
      {me && rows && (
        <div className="grid" style={{ marginTop: 16 }}>
          {rows.length === 0 && <Card><div className="empty">{t.noReports}</div></Card>}
          {rows.map((g) => (
            <Link key={g.id} to={`/track/${g.id}`}>
              <Card title={<span className="mono">{g.id}</span>} right={<span className="row-flex"><StageBadge stage={g.stage} label={t.stageName[g.stage]} /><StatusBadge status={g.status} label={t.status[g.status]} /></span>}>
                <b>{g.title}</b>
                <div className="small muted" style={{ marginTop: 4 }}>
                  {g.department} · {new Date(g.created_at).toLocaleDateString()} · {t.nowWith}: {g.authority}
                  {g.master_id !== g.id && ` · ${t.partOf} ${g.master_id}`}{g.report_count > 1 && ` · ${g.report_count} ${t.reports}`}
                </div>
                {g.status === 'Resolved' && !g.satisfaction && <div className="chip warn" style={{ marginTop: 8 }}>{t.confirmTitle}</div>}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
