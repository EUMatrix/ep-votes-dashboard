import { Routes, Route, Link } from 'react-router-dom'
import PasswordGate from './PasswordGate'
import SessionList from './pages/SessionList'
import DossierList from './pages/DossierList'
import VoteDetail from './pages/VoteDetail'

export default function App() {
  return (
    <PasswordGate>
    <div className="app">
      <header>
        <Link to="/" className="header-link">
          <h1>EP Plenary Votes</h1>
          <span className="subtitle">European Parliament Roll-Call Vote Explorer</span>
        </Link>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<SessionList />} />
          <Route path="/session/:date" element={<DossierList />} />
          <Route path="/vote/:voteId" element={<VoteDetail />} />
        </Routes>
      </main>
      <footer>
        <p>Data source: European Parliament &mdash; <a href="https://www.europarl.europa.eu/plenary/en/votes.html" target="_blank" rel="noreferrer">europarl.europa.eu</a></p>
      </footer>
    </div>
    </PasswordGate>
  )
}
