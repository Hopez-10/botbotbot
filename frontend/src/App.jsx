import { useEffect, useState } from 'react'
import {
  Activity,
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Compass,
  MapPin,
  MessageSquareText,
  Search,
  Sparkles,
  Store,
  TriangleAlert,
} from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function App() {
  const [run, setRun] = useState(null)
  const [leads, setLeads] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!run?.run_id) return undefined
    let active = true
    let timer

    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/runs/${run.run_id}`)
        if (!response.ok) throw new Error(`Status request failed (${response.status})`)
        const data = await response.json()
        if (!active) return
        setRun((current) => ({ ...current, ...data }))
        setLeads(data.leads || [])
        if (data.status === 'completed') {
          setBusy(false)
          return
        }
        timer = window.setTimeout(poll, 1000)
      } catch (requestError) {
        if (!active) return
        setError(`${requestError.message}. Check that the FastAPI server is running.`)
        setBusy(false)
      }
    }

    poll()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [run?.run_id])

  async function startDiscovery() {
    setBusy(true)
    setError('')
    setRun(null)
    setLeads([])
    try {
      const response = await fetch(`${API_BASE}/api/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_businesses: 5 }),
      })
      if (!response.ok) throw new Error(`Could not start discovery (${response.status})`)
      setRun(await response.json())
    } catch (requestError) {
      setError(`${requestError.message}. Start the FastAPI backend, then try again.`)
      setBusy(false)
    }
  }

  const searches = run?.searches || []
  const done = run?.status === 'completed'
  const withPhone = leads.filter((lead) => lead.phone).length
  const topState = searches[0]?.state || 'Awaiting run'
  const categorySummary = searches.length
    ? searches.map(({ category }) => category).join(' / ')
    : 'gyms / hotels / cafes'

  return (
    <div className="app-shell">
      <aside className="rail">
        <a className="brand-mark" href="#top" aria-label="Fieldnote home"><Compass size={21} strokeWidth={2.2} /></a>
        <div className="rail-rule" />
        <button className="rail-item active" aria-label="Lead discovery" title="Lead discovery"><Search size={18} /></button>
        <button className="rail-item" aria-label="Businesses" title="Businesses"><Store size={18} /></button>
        <button className="rail-item" aria-label="Activity" title="Activity"><Activity size={18} /></button>
        <div className="rail-spacer" />
        <button className="rail-item" aria-label="Help" title="Help"><CircleHelp size={18} /></button>
        <div className="avatar" title="Local workspace">F</div>
      </aside>

      <main id="top" className="workspace">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-slash">/</span><strong>Lead discovery</strong></div>
          <div className="topbar-right"><span className="mode-tag"><span className="mode-dot" /> PREVIEW MODE</span><span className="topbar-date">INDIA · LOCAL RUN</span></div>
        </header>

        <section className="page-intro">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> FIELDNOTE / PROSPECTING</div>
            <h1>Find your next<br className="mobile-break" /> <span>good fit.</span></h1>
            <p className="intro-copy">Discover local businesses, review their web presence, and prepare a tailored first touch.</p>
          </div>
          <div className="intro-stamp"><Compass size={20} /><span>INDIA<br />28 STATES</span></div>
        </section>

        <section className="control-strip" aria-label="Discovery controls">
          <div className="control-summary">
            <div className="control-icon"><MapPin size={18} /></div>
            <div><span className="field-label">SEARCH REGION</span><strong>{done ? topState : 'Random state selection'}</strong></div>
            <ChevronDown className="select-chevron" size={16} />
          </div>
          <div className="control-divider" />
          <div className="control-summary category-summary">
            <div className="control-icon coral"><Store size={18} /></div>
            <div><span className="field-label">BUSINESS TYPES</span><strong>{categorySummary}</strong></div>
            <ChevronDown className="select-chevron" size={16} />
          </div>
          <div className="control-spacer" />
          <div className="batch-note"><span className="field-label">CAP</span><strong>05 <small>businesses</small></strong></div>
          <button className="start-button" onClick={startDiscovery} disabled={busy}>
            {busy ? <span className="button-spinner" /> : <Search size={16} />}
            <span>{busy ? 'Discovering' : 'Start discovery'}</span>
            {!busy && <ArrowUpRight size={15} />}
          </button>
        </section>

        <div className="run-line" aria-live="polite">
          <span className={`run-indicator ${busy ? 'is-running' : done ? 'is-done' : ''}`} />
          <span>{busy ? `Searching ${run?.current_query || 'Google Maps'}...` : done ? `Run complete · ${run?.source || 'Google Maps'}` : 'Ready when you are'}</span>
          {busy && <span className="run-progress">{run?.progress || 0} / 3 searches</span>}
          {done && <span className="run-progress">Updated just now</span>}
        </div>

        {error && <div className="error-banner"><TriangleAlert size={17} /><span>{error}</span></div>}
        {done && run.errors?.length > 0 && <div className="notice-banner"><TriangleAlert size={17} /><span>{run.errors.length} search issue(s). Results shown are whatever the run could collect; details are available in the backend terminal.</span></div>}

        <section className="metrics" aria-label="Run summary">
          <div className="metric"><div className="metric-top"><span>BUSINESSES FOUND</span><Store size={15} /></div><strong>{done ? leads.length : '—'}</strong><small>{done ? 'Businesses across selected searches' : 'Results appear after discovery'}</small></div>
          <div className="metric"><div className="metric-top"><span>PHONE NUMBERS</span><MessageSquareText size={15} /></div><strong>{done ? withPhone : '—'}</strong><small>{done ? 'Visible in Maps listing' : 'Extracted where available'}</small></div>
          <div className="metric"><div className="metric-top"><span>SEARCHES</span><MapPin size={15} /></div><strong>{done ? searches.length : '03'}</strong><small>Different states, randomized</small></div>
          <div className="metric metric-accent"><div className="metric-top"><span>OUTREACH</span><Sparkles size={15} /></div><strong>Drafts</strong><small>AI-assisted · delivery disabled</small></div>
        </section>

        <section className="results-section">
          <div className="section-heading">
            <div><div className="section-kicker">PROSPECT REGISTER <span>{done ? String(leads.length).padStart(2, '0') : '—'}</span></div><h2>Business opportunities</h2></div>
            <div className="table-tools"><span className="filter-chip"><span className="filter-dot" /> Website status</span><span className="sort-label"><Clock3 size={14} /> Latest run</span></div>
          </div>

          <div className="table-frame">
            <div className="table-scroll">
              <table>
                <thead><tr><th>STATE / TYPE</th><th>BUSINESS</th><th>WEBSITE</th><th>PHONE</th><th>MAPS</th><th>GROK MESSAGE PREVIEW</th><th>MESSAGE STATUS</th></tr></thead>
                <tbody>
                  {leads.map((lead, index) => (
                    <tr key={lead.id || `${lead.name}-${index}`}>
                      <td><div className="state-cell"><span className="state-pin"><MapPin size={13} /></span><div><strong>{lead.state}</strong><small>{lead.category}</small></div></div></td>
                      <td><div className="business-cell"><strong>{lead.name}</strong><small>Google Maps listing</small></div></td>
                      <td>{lead.website ? <a className="website-link" href={lead.website} target="_blank" rel="noreferrer">Has website <ArrowUpRight size={12} /></a> : <span className="missing-website">No website listed</span>}</td>
                      <td>{lead.phone ? <a className="phone-link" href={`tel:${lead.phone}`}>{lead.phone}</a> : <span className="empty-value">Not listed</span>}</td>
                      <td><a className="map-link" href={lead.maps_url} target="_blank" rel="noreferrer" aria-label={`Open ${lead.name} in Maps`}><MapPin size={15} /><span>Open map</span><ArrowUpRight size={12} /></a></td>
                      <td><p className="message-preview">{lead.message}</p></td>
                      <td>{lead.message_status === 'ready' ? <span className="delivery-state preview-ready"><span className="delivery-icon"><Check size={12} /></span><span>Message ready<small>Not sent</small></span></span> : <span className="delivery-state preparing"><span className="mini-spinner" /><span>Preparing<small>Preview only</small></span></span>}</td>
                    </tr>
                  ))}
                  {!leads.length && <tr className="empty-row"><td colSpan="7"><div className="empty-state"><div className="empty-icon"><Search size={20} /></div><strong>{busy ? 'Looking across the map...' : 'Your prospect list starts here'}</strong><span>{busy ? 'Searching gyms, hotels, and cafes in three randomly selected states.' : 'Start a discovery run to find up to five businesses and prepare a tailored message.'}</span>{busy && <div className="empty-progress"><i style={{ width: `${Math.max(8, ((run?.progress || 0) / 3) * 100)}%` }} /></div>}</div></td></tr>}
                </tbody>
              </table>
            </div>
            <footer className="table-footer"><span><span className="footer-led" /> {done ? `${leads.length} businesses in this run` : 'Waiting for a discovery run'}</span><span>MESSAGE PREVIEWS ARE NOT SENT</span></footer>
          </div>
        </section>
        <footer className="page-footer"><span>FIELDNOTE <span className="footer-sep">/</span> LOCAL BUSINESS RESEARCH</span><span>MAPS DATA MAY BE INCOMPLETE</span></footer>
      </main>
    </div>
  )
}

export default App