import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { supabase } from '../supabaseClient'

const MONTHS = [
  '', 'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00')
  return `${d.getDate()} ${MONTHS[d.getMonth() + 1]} ${d.getFullYear()}`
}

function formatDateLong(dateStr) {
  const d = new Date(dateStr + 'T12:00:00')
  const weekday = d.toLocaleDateString('en-US', { weekday: 'long' })
  return `${weekday}, ${d.getDate()} ${MONTHS[d.getMonth() + 1]} ${d.getFullYear()}`
}

const REPORT_TYPE_LABELS = { Leg: 'Legislative', Non: 'Non-legislative', Bud: 'Budget' }

async function fetchAllRows() {
  const PAGE = 1000
  let all = []
  let offset = 0
  while (true) {
    const { data, error } = await supabase
      .from('Plenary_votes_main')
      .select('"Vote ID", "Date", "Report name", "Final vote?", "Policy category1", "report_type", "Outcome of the vote", "Subject of vote"')
      .range(offset, offset + PAGE - 1)
    if (error) { console.error(error); break }
    all = all.concat(data)
    if (data.length < PAGE) break
    offset += PAGE
  }
  return all
}

export default function SessionList() {
  const [allData, setAllData] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedType, setSelectedType] = useState('')
  const [selectedDate, setSelectedDate] = useState('')
  const [view, setView] = useState('sessions') // 'sessions' or 'dossiers'

  useEffect(() => {
    fetchAllRows().then(data => { setAllData(data); setLoading(false) })
  }, [])

  // Extract filter options
  const { dates, categories, dossierList, sessionList, stats } = useMemo(() => {
    const dateSet = new Set()
    const catSet = new Set()
    const byDate = {}
    const byDossier = {}

    for (const row of allData) {
      const date = (row['Date'] || '').split(' ')[0].split('T')[0]
      if (!date) continue
      dateSet.add(date)

      const cat = row['Policy category1']
      if (cat) catSet.add(cat)

      // Sessions
      if (!byDate[date]) byDate[date] = { date, dossiers: new Set(), votes: 0, finals: 0, categories: new Set(), types: new Set() }
      byDate[date].dossiers.add(row['Report name'])
      byDate[date].votes++
      if (row['Final vote?'] === 1) byDate[date].finals++
      if (cat) byDate[date].categories.add(cat)
      if (row['report_type']) byDate[date].types.add(row['report_type'])

      // Dossiers
      const name = row['Report name'] || 'Untitled'
      const key = `${date}|||${name}`
      if (!byDossier[key]) byDossier[key] = {
        name, date, votes: 0, finals: 0,
        category: cat || '', type: row['report_type'] || '',
        outcome: null,
      }
      byDossier[key].votes++
      if (row['Final vote?'] === 1) {
        byDossier[key].finals++
        byDossier[key].outcome = row['Outcome of the vote']
      }
    }

    const dates = [...dateSet].sort().reverse()
    const categories = [...catSet].sort()

    const sessionList = Object.values(byDate)
      .map(s => ({ ...s, dossiers: s.dossiers.size, categories: [...s.categories], types: [...s.types] }))
      .sort((a, b) => b.date.localeCompare(a.date))

    const dossierList = Object.values(byDossier)
      .sort((a, b) => b.date.localeCompare(a.date) || a.name.localeCompare(b.name))

    return {
      dates,
      categories,
      dossierList,
      sessionList,
      stats: { dates: dates.length, dossiers: new Set(allData.map(r => r['Report name'])).size, votes: allData.length },
    }
  }, [allData])

  // Apply filters
  const filteredSessions = useMemo(() => {
    return sessionList.filter(s => {
      if (selectedDate && s.date !== selectedDate) return false
      if (selectedCategory && !s.categories.includes(selectedCategory)) return false
      if (selectedType && !s.types.includes(selectedType)) return false
      if (search) {
        // Check if any dossier in this session matches
        const q = search.toLowerCase()
        const sessionDossiers = dossierList.filter(d => d.date === s.date)
        return sessionDossiers.some(d => d.name.toLowerCase().includes(q))
      }
      return true
    })
  }, [sessionList, dossierList, selectedDate, selectedCategory, selectedType, search])

  const filteredDossiers = useMemo(() => {
    return dossierList.filter(d => {
      if (selectedDate && d.date !== selectedDate) return false
      if (selectedCategory && d.category !== selectedCategory) return false
      if (selectedType && d.type !== selectedType) return false
      if (search && !d.name.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [dossierList, selectedDate, selectedCategory, selectedType, search])

  const hasFilters = search || selectedCategory || selectedType || selectedDate

  if (loading) return <div className="loading"><div className="spinner" />Loading plenary votes data...</div>

  return (
    <div>
      {/* Stats bar */}
      <div className="stats-bar">
        <div className="stat">
          <span className="stat-value">{stats.dates}</span>
          <span className="stat-label">Plenary days</span>
        </div>
        <div className="stat">
          <span className="stat-value">{stats.dossiers}</span>
          <span className="stat-label">Dossiers</span>
        </div>
        <div className="stat">
          <span className="stat-value">{stats.votes.toLocaleString()}</span>
          <span className="stat-label">Roll-call votes</span>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <input
          type="text"
          className="filter-search"
          placeholder="Search dossiers..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className="filter-select" value={selectedDate} onChange={e => setSelectedDate(e.target.value)}>
          <option value="">All dates</option>
          {dates.map(d => <option key={d} value={d}>{formatDate(d)}</option>)}
        </select>
        <select className="filter-select" value={selectedCategory} onChange={e => setSelectedCategory(e.target.value)}>
          <option value="">All policy areas</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="filter-select" value={selectedType} onChange={e => setSelectedType(e.target.value)}>
          <option value="">All types</option>
          <option value="Leg">Legislative</option>
          <option value="Non">Non-legislative</option>
          <option value="Bud">Budget</option>
        </select>
        {hasFilters && (
          <button className="filter-clear" onClick={() => { setSearch(''); setSelectedCategory(''); setSelectedType(''); setSelectedDate('') }}>
            Clear filters
          </button>
        )}
      </div>

      {/* View toggle */}
      <div className="view-toggle">
        <button className={view === 'sessions' ? 'active' : ''} onClick={() => setView('sessions')}>
          By session ({filteredSessions.length})
        </button>
        <button className={view === 'dossiers' ? 'active' : ''} onClick={() => setView('dossiers')}>
          By dossier ({filteredDossiers.length})
        </button>
      </div>

      {/* Session view */}
      {view === 'sessions' && (
        <div>
          {filteredSessions.length === 0 && <div className="loading" style={{ padding: 40 }}>No sessions match your filters.</div>}
          {filteredSessions.map(s => (
            <div className="card session-card" key={s.date}>
              <Link to={`/session/${s.date}`} className="card-link">
                <div className="date">{formatDateLong(s.date)}</div>
                <div className="meta">
                  <span>{s.dossiers} dossier{s.dossiers !== 1 ? 's' : ''}</span>
                  <span>{s.votes} vote{s.votes !== 1 ? 's' : ''}</span>
                  {s.finals > 0 && <span>{s.finals} final</span>}
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}

      {/* Dossier view */}
      {view === 'dossiers' && (
        <div>
          {filteredDossiers.length === 0 && <div className="loading" style={{ padding: 40 }}>No dossiers match your filters.</div>}
          {filteredDossiers.map((d, i) => (
            <div className="card dossier-card" key={`${d.date}-${d.name}-${i}`}>
              <Link to={`/session/${d.date}`} className="card-link">
                <div className="dossier-title">{d.name}</div>
                <div className="dossier-meta">
                  <span style={{ color: 'var(--gray-500)' }}>{formatDate(d.date)}</span>
                  <span>{d.votes} vote{d.votes !== 1 ? 's' : ''}</span>
                  {d.type && <span className="badge badge-type">{REPORT_TYPE_LABELS[d.type] || d.type}</span>}
                  {d.category && <span className="badge badge-type" style={{ background: '#f0fdf4', color: '#166534' }}>{d.category}</span>}
                  {d.outcome === '+' && <span className="badge badge-adopted">Adopted</span>}
                  {d.outcome === '-' && <span className="badge badge-rejected">Rejected</span>}
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
