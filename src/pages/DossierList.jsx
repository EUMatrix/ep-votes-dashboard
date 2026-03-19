import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { supabase } from '../supabaseClient'

const MONTHS = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00')
  return `${d.getDate()} ${MONTHS[d.getMonth() + 1]} ${d.getFullYear()}`
}

const SHORT_GROUPS = {
  'Group of the European People\'s Party (Christian Democrats)': 'EPP',
  'Group of the Progressive Alliance of Socialists and Democrats in the European Parliament': 'S&D',
  'Renew Europe Group': 'Renew',
  'Group of the Greens/European Free Alliance': 'Greens/EFA',
  'European Conservatives and Reformists Group': 'ECR',
  'Patriots for Europe Group': 'PfE',
  'The Left group in the European Parliament - GUE/NGL': 'The Left',
  'Europe of Sovereign Nations Group': 'ESN',
  'Non-attached Members': 'NI',
}

const GROUP_ORDER = ['EPP', 'S&D', 'Renew', 'Greens/EFA', 'ECR', 'PfE', 'The Left', 'ESN', 'NI']

export default function DossierList() {
  const { date } = useParams()
  const [dossiers, setDossiers] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(new Set())
  const [epgData, setEpgData] = useState({})

  useEffect(() => {
    async function load() {
      // Fetch votes for this date — use like to handle both "2026-03-12" and "2026-03-12 00:00:00"
      const { data, error } = await supabase
        .from('Plenary_votes_main')
        .select('*')
        .like('Date', date + '%')
        .order('Vote ID', { ascending: true })

      const rows = (!error && data) ? data : []
      processData(rows)

      // Fetch EPG group votes for this date
      const voteIds = rows.map(v => v['Vote ID']).filter(Boolean)
      if (voteIds.length > 0) {
        const { data: epg } = await supabase
          .from('epg_rcv_votes')
          .select('vote_id, political_group_code, vote_value, meps_for, meps_against, meps_abstain')
          .in('vote_id', voteIds)

        if (epg) {
          const byVote = {}
          for (const row of epg) {
            if (!byVote[row.vote_id]) byVote[row.vote_id] = []
            byVote[row.vote_id].push(row)
          }
          setEpgData(byVote)
        }
      }
    }

    function processData(data) {
      // Group by Report name
      const byReport = {}
      for (const row of data) {
        const name = row['Report name'] || 'Untitled'
        if (!byReport[name]) byReport[name] = { name, votes: [], reportType: row.report_type }
        byReport[name].votes.push(row)
      }
      setDossiers(Object.values(byReport))
      // Auto-expand if only 1 dossier
      if (Object.keys(byReport).length === 1) {
        setExpanded(new Set([Object.keys(byReport)[0]]))
      }
      setLoading(false)
    }
    load()
  }, [date])

  function toggle(name) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  if (loading) return <div className="loading"><div className="spinner" />Loading votes...</div>

  return (
    <div>
      <div className="breadcrumb">
        <Link to="/">Sessions</Link>
        <span className="sep">/</span>
        <span>{formatDate(date)}</span>
      </div>

      <h2 style={{ fontSize: 18, marginBottom: 20, color: 'var(--gray-700)' }}>
        {formatDate(date)} &mdash; {dossiers.length} dossier{dossiers.length !== 1 ? 's' : ''}, {dossiers.reduce((n, d) => n + d.votes.length, 0)} votes
      </h2>

      {dossiers.map(d => {
        const isOpen = expanded.has(d.name)
        const finalVote = d.votes.find(v => v['Final vote?'] === 1)
        const outcome = finalVote?.['Outcome of the vote']
        return (
          <div className="dossier-card" key={d.name}>
            <div
              className="card dossier-header-card"
              style={{ cursor: 'pointer', marginBottom: 0, borderRadius: isOpen ? 'var(--radius) var(--radius) 0 0' : 'var(--radius)' }}
              onClick={() => toggle(d.name)}
            >
              <div className="card-link">
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span className={`toggle-arrow ${isOpen ? 'open' : ''}`}>&#9654;</span>
                  <div style={{ flex: 1 }}>
                    <div className="dossier-title">{d.name}</div>
                    <div className="dossier-meta">
                      <span>{d.votes.length} vote{d.votes.length !== 1 ? 's' : ''}</span>
                      {d.reportType && <span className="badge badge-type">{d.reportType}</span>}
                      {outcome === '+' && <span className="badge badge-adopted">Adopted</span>}
                      {outcome === '-' && <span className="badge badge-rejected">Rejected</span>}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {isOpen && (
              <div className="card" style={{ borderRadius: '0 0 var(--radius) var(--radius)', borderTop: 'none' }}>
                {d.votes.map(v => {
                  const vid = v['Vote ID']
                  const [yes, no, abs] = (v['Yes, no, abs'] || '').split(',').map(s => parseInt(s?.trim()) || 0)
                  const groups = epgData[vid] || []
                  return (
                    <Link
                      to={`/vote/${vid}`}
                      className="vote-row"
                      key={vid}
                    >
                      <div className="subject">
                        {v['Subject of vote']}
                        {v['Final vote?'] === 1 && <span className="badge badge-final" style={{ marginLeft: 8 }}>Final</span>}
                      </div>
                      <div className="group-votes-row">
                        {groups.sort((a, b) => {
                          const ai = GROUP_ORDER.indexOf(SHORT_GROUPS[a.political_group_code] || '')
                          const bi = GROUP_ORDER.indexOf(SHORT_GROUPS[b.political_group_code] || '')
                          return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
                        }).map(g => {
                          const code = SHORT_GROUPS[g.political_group_code] || g.political_group_code
                          const icon = g.vote_value === '+' ? '\u{1F44D}' : g.vote_value === '-' ? '\u{1F44E}' : '\u{270B}'
                          const cls = g.vote_value === '+' ? 'gv-for' : g.vote_value === '-' ? 'gv-against' : 'gv-abstain'
                          return (
                            <span
                              key={g.political_group_code}
                              className={`gv-chip ${cls}`}
                              title={`${g.political_group_code}: ${g.meps_for} for / ${g.meps_against} against / ${g.meps_abstain} abstain`}
                            >
                              <span className="gv-code">{code}</span>
                              <span className="gv-icon">{icon}</span>
                            </span>
                          )
                        })}
                      </div>
                      <div className="tally">
                        <span style={{ color: 'var(--green)' }}>{yes}</span>
                        {' / '}
                        <span style={{ color: 'var(--red)' }}>{no}</span>
                        {' / '}
                        <span style={{ color: 'var(--orange)' }}>{abs}</span>
                      </div>
                      <span className={`badge ${v['Outcome of the vote'] === '+' ? 'badge-adopted' : 'badge-rejected'}`}>
                        {v['Outcome of the vote'] === '+' ? 'Adopted' : 'Rejected'}
                      </span>
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
