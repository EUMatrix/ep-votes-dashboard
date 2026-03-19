import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { supabase } from '../supabaseClient'

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

function shortGroup(full) {
  return SHORT_GROUPS[full] || full
}

export default function VoteDetail() {
  const { voteId } = useParams()
  const [vote, setVote] = useState(null)
  const [mepVotes, setMepVotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeGroup, setActiveGroup] = useState(null)
  const [countryFilter, setCountryFilter] = useState('')

  useEffect(() => {
    async function load() {
      // Fetch vote metadata
      const { data: voteData } = await supabase
        .from('Plenary_votes_main')
        .select('*')
        .eq('Vote ID', parseInt(voteId))
        .single()

      if (voteData) setVote(voteData)

      // Fetch individual MEP votes
      const { data: meps } = await supabase
        .from('meps_rcv_votes')
        .select('website_id, mep_name, country, political_group, national_party, vote_value')
        .eq('vote_id', parseInt(voteId))
        .order('political_group', { ascending: true })
        .order('mep_name', { ascending: true })

      if (meps) setMepVotes(meps)
      setLoading(false)
    }
    load()
  }, [voteId])

  if (loading) return <div className="loading"><div className="spinner" />Loading vote details...</div>
  if (!vote) return <div className="loading">Vote not found</div>

  const date = vote['Date']?.split(' ')[0] || vote['Date']
  const [yes, no, abs] = (vote['Yes, no, abs'] || '').split(',').map(s => parseInt(s?.trim()) || 0)
  const total = yes + no + abs || 1

  // Group MEP votes
  const groups = {}
  for (const m of mepVotes) {
    const g = shortGroup(m.political_group)
    if (!groups[g]) groups[g] = { name: m.political_group, short: g, meps: [], for: 0, against: 0, abstain: 0 }
    groups[g].meps.push(m)
    if (m.vote_value === '+') groups[g].for++
    else if (m.vote_value === '-') groups[g].against++
    else groups[g].abstain++
  }

  const countries = [...new Set(mepVotes.map(m => m.country).filter(Boolean))].sort()

  const sortedGroups = GROUP_ORDER
    .filter(g => groups[g])
    .map(g => groups[g])
    .concat(
      Object.values(groups).filter(g => !GROUP_ORDER.includes(g.short))
    )

  return (
    <div>
      <div className="breadcrumb">
        <Link to="/">Sessions</Link>
        <span className="sep">/</span>
        <Link to={`/session/${date}`}>{date}</Link>
        <span className="sep">/</span>
        <span>Vote #{voteId}</span>
      </div>

      {/* Vote header */}
      <div className="vote-header">
        <h2>{vote['Report name']}</h2>
        <div className="vote-subject">{vote['Subject of vote']}</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          <span className={`badge ${vote['Outcome of the vote'] === '+' ? 'badge-adopted' : 'badge-rejected'}`}>
            {vote['Outcome of the vote'] === '+' ? 'Adopted' : 'Rejected'}
          </span>
          {vote['Final vote?'] === 1 && <span className="badge badge-final">Final Vote</span>}
          {vote.report_type && <span className="badge badge-type">{vote.report_type}</span>}
        </div>

        <div className="tally-bar">
          <div className="for" style={{ width: `${(yes / total) * 100}%` }} title={`For: ${yes}`} />
          <div className="against" style={{ width: `${(no / total) * 100}%` }} title={`Against: ${no}`} />
          <div className="abstain" style={{ width: `${(abs / total) * 100}%` }} title={`Abstention: ${abs}`} />
        </div>
        <div className="tally-labels">
          <span className="for-label">For: {yes}</span>
          <span className="against-label">Against: {no}</span>
          <span className="abstain-label">Abstention: {abs}</span>
          <span style={{ color: 'var(--gray-500)' }}>Total: {yes + no + abs}</span>
        </div>
      </div>

      {/* Amendment text / Summary */}
      {(vote['Summary'] || vote['Amended Text'] || vote['Original text']) && (
        <div className="text-panel">
          {vote['Summary'] && (
            <>
              <h3>Summary</h3>
              <div className="summary">{vote['Summary']}</div>
            </>
          )}
          {vote['Amended Text'] && (
            <div style={{ marginTop: vote['Summary'] ? 16 : 0 }}>
              <h3>Amendment Text</h3>
              <div className="text-content">{vote['Amended Text']}</div>
            </div>
          )}
          {vote['Original text'] && (
            <div style={{ marginTop: (vote['Summary'] || vote['Amended Text']) ? 16 : 0 }}>
              <h3>Original Text</h3>
              <div className="text-content">{vote['Original text']}</div>
            </div>
          )}
        </div>
      )}

      {/* MEP votes by group */}
      {mepVotes.length > 0 ? (
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: 'var(--gray-700)' }}>
            Individual MEP Votes ({mepVotes.length} MEPs)
          </h3>

          {/* Group overview — all groups at a glance */}
          <div className="group-overview">
            {sortedGroups.map(g => {
              const total = g.for + g.against + g.abstain
              const majority = g.for >= g.against ? (g.for >= g.abstain ? 'for' : 'abstain') : (g.against >= g.abstain ? 'against' : 'abstain')
              return (
                <div
                  key={g.short}
                  className={`group-overview-card ${activeGroup === g.short ? 'active' : ''}`}
                  onClick={() => setActiveGroup(activeGroup === g.short ? null : g.short)}
                >
                  <div className="go-name">{g.short}</div>
                  <div className="go-bar">
                    <div className="go-for" style={{ width: `${(g.for / total) * 100}%` }} />
                    <div className="go-against" style={{ width: `${(g.against / total) * 100}%` }} />
                    <div className="go-abstain" style={{ width: `${(g.abstain / total) * 100}%` }} />
                  </div>
                  <div className="go-counts">
                    <span className="for-label">{g.for}</span>
                    <span className="against-label">{g.against}</span>
                    <span className="abstain-label">{g.abstain}</span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* MEP detail table — show selected group or all */}
          <div className="mep-table-container">
            <div className="mep-table-header">
              <span>{activeGroup ? `${activeGroup} members` : 'All MEPs'}</span>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <select
                  className="filter-select"
                  style={{ padding: '4px 8px', fontSize: 12 }}
                  value={countryFilter}
                  onChange={e => setCountryFilter(e.target.value)}
                >
                  <option value="">All countries</option>
                  {countries.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                {(activeGroup || countryFilter) && (
                  <button className="mep-table-clear" onClick={() => { setActiveGroup(null); setCountryFilter('') }}>
                    Clear
                  </button>
                )}
              </div>
            </div>
            <div className="mep-grid">
              {(activeGroup ? sortedGroups.filter(g => g.short === activeGroup) : sortedGroups).map(g =>
                g.meps.filter(m => !countryFilter || m.country === countryFilter).map(m => (
                  <div className="mep-cell" key={`${g.short}-${m.website_id}`}>
                    <span className={`mep-icon ${m.vote_value === '+' ? 'for' : m.vote_value === '-' ? 'against' : 'abstain'}`}>
                      {m.vote_value === '+' ? '\u{1F44D}' : m.vote_value === '-' ? '\u{1F44E}' : '\u{270B}'}
                    </span>
                    <span className="mep-cell-name">{m.mep_name}</span>
                    <span className="mep-cell-party">{m.national_party}</span>
                    <span className="mep-cell-country">{m.country}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="loading" style={{ padding: 30 }}>
          No individual MEP voting data available for this vote.
        </div>
      )}
    </div>
  )
}
