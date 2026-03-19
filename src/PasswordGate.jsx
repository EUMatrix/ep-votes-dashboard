import { useState } from 'react'

const HASH = '5a8dd3ad0756a93ded72b823b19dd877' // md5 of "Dashepvote"

function md5Simple(str) {
  // Simple string comparison — the real protection is that the data comes from Supabase
  // with its own RLS. This gate just prevents casual browsing.
  return str
}

export default function PasswordGate({ children }) {
  const [authed, setAuthed] = useState(() => sessionStorage.getItem('ep_dash_auth') === 'true')
  const [input, setInput] = useState('')
  const [error, setError] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (input === 'Dashepvote') {
      sessionStorage.setItem('ep_dash_auth', 'true')
      setAuthed(true)
    } else {
      setError(true)
      setTimeout(() => setError(false), 2000)
    }
  }

  if (authed) return children

  return (
    <div className="gate-overlay">
      <div className="gate-box">
        <div className="gate-icon">&#127466;&#127482;</div>
        <h2>EP Plenary Votes Dashboard</h2>
        <p>Enter the access code to continue</p>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            className="gate-input"
            placeholder="Access code"
            value={input}
            onChange={e => setInput(e.target.value)}
            autoFocus
          />
          <button type="submit" className="gate-btn">Enter</button>
        </form>
        {error && <p className="gate-error">Incorrect code</p>}
      </div>
    </div>
  )
}
