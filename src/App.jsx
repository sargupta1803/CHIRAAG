import React, { useEffect, useState } from 'react'
import { getRoute, getSegment, USE_MOCK_DATA } from './lib/api'
import { Header } from './components/Header'
import { RouteComparison } from './components/RouteComparison'
import { HeroMetric } from './components/HeroMetric'
import { TimeControl } from './components/TimeControl'
import { DetourControl } from './components/DetourControl'
import { UnknownPolicy as UnknownPolicyControl } from './components/UnknownPolicy'
import { EvidencePanel } from './components/EvidencePanel'
import { MapView } from './components/MapView'


export default function App() {
  const [hour, setHour] = useState(23)
  const [detour, setDetour] = useState(20)
  const [policy, setPolicy] = useState('neutral')
  const [from, setFrom] = useState('Connaught Place')
  const [to, setTo] = useState('India Gate')
  const [journey, setJourney] = useState({ from: 'Connaught Place', to: 'India Gate' })
  const [data, setData] = useState(null)
  const [selectedRoute, setSelectedRoute] = useState('safe')
  const [selectedEvidence, setSelectedEvidence] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(false)
    getRoute(hour, detour, policy, journey.from, journey.to)
      .then(route => active && setData(route))
      .catch(() => active && setError(true))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [hour, detour, policy, journey])

  async function selectSegment(id) {
    try { setSelectedEvidence(await getSegment(id)) } catch { setError(true) }
  }

  function findRoute(event) {
    event.preventDefault()
    setJourney({ from: from.trim() || 'Connaught Place', to: to.trim() || 'India Gate' })
    setSelectedRoute('safe')
  }

  return <main className="app-shell">
    {data && <MapView data={data} selected={selectedRoute} selectedSegment={selectedEvidence?.seg_id ?? null} onSegment={selectSegment} />}
    <Header />
    <form className="route-search" onSubmit={findRoute} aria-label="Find a safer route">
      <div className="place-field"><label htmlFor="from">FROM</label><input id="from" value={from} onChange={e => setFrom(e.target.value)} /></div>
      <span className="search-connector" aria-hidden="true">&darr;</span>
      <div className="place-field"><label htmlFor="to">TO</label><input id="to" value={to} onChange={e => setTo(e.target.value)} /></div>
      <button className="find-route" type="submit">Find safer route <span>&rarr;</span></button>
    </form>
    <aside className="route-panel">
      {loading && <div className="quiet-loading">Updating route <i /></div>}
      {error && <div className="quiet-error">Route data unavailable <span>Using demo fixture</span></div>}
      {data && <>
        <div className="recommendation">
          <p className="eyebrow">CHIRAAG RECOMMENDS</p>
          <div className="recommendation-title">Safer route</div>
          <div className="route-duration">{data.safest.length_m} m <span>&middot; ~11 min</span></div>
          <HeroMetric delta={data.delta} />
          <button className="use-route" onClick={() => setSelectedRoute('safe')}>Use this route <span>&rarr;</span></button>
        </div>
        <RouteComparison data={data} selected={selectedRoute} onSelect={setSelectedRoute} />
        <div className="compact-controls"><TimeControl hour={hour} onChange={setHour} /><DetourControl value={detour} onChange={setDetour} /></div>
        <UnknownPolicyControl policy={policy} onChange={setPolicy} />
      </>}
      <div className="panel-footer"><span className="status-indicator">{USE_MOCK_DATA ? 'LOCAL DEMO DATA' : 'LIVE DATA'}</span><span>Click a street for proof</span></div>
    </aside>
    <EvidencePanel evidence={selectedEvidence} onClose={() => setSelectedEvidence(null)} />
  </main>
}
