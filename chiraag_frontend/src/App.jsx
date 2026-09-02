import React, { useEffect, useState, useRef } from 'react'
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
  const [journey, setJourney] = useState({
    from: 'Connaught Place',
    to: 'India Gate',
    fromCoords: null,
    toCoords: null,
  })
  const [data, setData] = useState(null)
  const [selectedRoute, setSelectedRoute] = useState('safe')
  const [selectedEvidence, setSelectedEvidence] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [fromSuggestions, setFromSuggestions] = useState([])
  const [toSuggestions, setToSuggestions] = useState([])
  const [activeSearch, setActiveSearch] = useState(null)
  const searchRequest = useRef(0)
  const searchTimer = useRef(null)

  useEffect(() => {
    if (!journey.fromCoords || !journey.toCoords) return

    let active = true

    setLoading(true)
    setError(false)

    getRoute(
      hour,
      detour,
      policy,
      journey.fromCoords,
      journey.toCoords
    )
      .then(route => {
        if (!active) return

        setData(route)
        setSelectedRoute('safe')
      })
      .catch(error => {
        console.error(error)
        if (active) setError(true)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [hour, detour, policy, journey])

  async function selectSegment(id) {
    try { setSelectedEvidence(await getSegment(id)) } catch { setError(true) }
  }

  async function searchPlaces(query, setter) {
    clearTimeout(searchTimer.current)

    if (query.trim().length < 2) {
      setter([])
      return
    }

    const requestId = ++searchRequest.current

    searchTimer.current = setTimeout(async () => {
      try {
        const response = await fetch(
          `https://api.maptiler.com/geocoding/${encodeURIComponent(
            `${query}, New Delhi`
          )}.json?key=${import.meta.env.VITE_MAPTILER_KEY}&country=in&proximity=77.2295,28.6129&types=poi,address&autocomplete=true&limit=8`
        )

        const result = await response.json()

        if (requestId !== searchRequest.current) return

        const candidates = result.features || []

        const enriched = await Promise.all(
          candidates.map(async place => {
            const [lon, lat] = place.geometry.coordinates

            try {
              const reverseResponse = await fetch(
                `https://api.maptiler.com/geocoding/${lon},${lat}.json?key=${import.meta.env.VITE_MAPTILER_KEY}&types=address&limit=1`
              )

              const reverseData = await reverseResponse.json()

              const address =
                reverseData.features?.[0]?.place_name ||
                reverseData.features?.[0]?.text ||
                ''

              return {
                ...place,
                branchAddress: address,
              }
            } catch {
              return {
                ...place,
                branchAddress: place.place_name || 'Delhi',
              }
            }
          })
        )

        if (requestId !== searchRequest.current) return

        const unique = []
        const seen = new Set()

        for (const place of enriched) {
          const [lon, lat] = place.geometry.coordinates

          const key =
            `${place.text}|` +
            `${lon.toFixed(5)}|` +
            `${lat.toFixed(5)}`

          if (seen.has(key)) continue

          seen.add(key)
          unique.push(place)
        }

        setter(unique.slice(0, 6))
      } catch (error) {
        console.error(error)

        if (requestId === searchRequest.current) {
          setter([])
        }
      }
    }, 350)
  }

  function getPlaceArea(place) {
    const context = place.context || []

    const preferred = [
      'neighbourhood',
      'locality',
      'municipality',
      'road',
    ]

    for (const kind of preferred) {
      const item = context.find(
        entry =>
          entry.kind === kind ||
          entry.place_designation === kind
      )

      if (item?.text) return item.text
    }

    return place.place_name || 'Delhi'
  }

  function getDistanceKm(place) {
    const [lon, lat] = place.geometry.coordinates

    const refLon = 77.2295
    const refLat = 28.6129

    const latDiff = (lat - refLat) * 111
    const lonDiff =
      (lon - refLon) *
      111 *
      Math.cos((refLat * Math.PI) / 180)

    return Math.sqrt(
      latDiff * latDiff +
      lonDiff * lonDiff
    )
  }

  async function findRoute(event) {
    event.preventDefault()

    const fromPlace = from.trim() || 'Connaught Place'
    const toPlace = to.trim() || 'India Gate'

    try {
      setLoading(true)
      setError(false)

      const [fromResponse, toResponse] = await Promise.all([
        fetch(
          `https://api.maptiler.com/geocoding/${encodeURIComponent(
            `${fromPlace}, New Delhi`
          )}.json?key=${import.meta.env.VITE_MAPTILER_KEY}&country=in&proximity=77.2295,28.6129&types=poi,address&limit=1`
        ),
        fetch(
          `https://api.maptiler.com/geocoding/${encodeURIComponent(
            `${toPlace}, New Delhi`
          )}.json?key=${import.meta.env.VITE_MAPTILER_KEY}&country=in&proximity=77.2295,28.6129&types=poi,address&limit=1`
        ),
      ])

      const fromData = await fromResponse.json()
      const toData = await toResponse.json()

      if (!fromData.features?.length || !toData.features?.length) {
        throw new Error('Location not found')
      }

      const [fromLon, fromLat] =
        fromData.features[0].geometry.coordinates

      const [toLon, toLat] =
        toData.features[0].geometry.coordinates

      setJourney({
        from: fromPlace,
        to: toPlace,
        fromCoords: {
          lat: fromLat,
          lon: fromLon,
        },
        toCoords: {
          lat: toLat,
          lon: toLon,
        },
      })
    } catch (error) {
      console.error(error)
      setError(true)
      setLoading(false)
    }
  }

  return <main className="app-shell">
    {data && <MapView
      data={data}
      selected={selectedRoute}
      selectedSegment={selectedEvidence?.road_id ?? null}
      onSegment={selectSegment}
      fromCoords={journey.fromCoords}
      toCoords={journey.toCoords}
      fromName={journey.from}
      toName={journey.to}
    />}
    <Header />
    <form className="route-search" onSubmit={findRoute} aria-label="Find a safer route">
      <div
        className="place-field"
        style={{ position: 'relative' }}
      >
        <label htmlFor="from">FROM</label>

        <input
          id="from"
          value={from}
          onFocus={() => setActiveSearch('from')}
          onChange={e => {
            const value = e.target.value
            setFrom(value)

            setJourney(prev => ({
              ...prev,
              fromCoords: null,
            }))

            searchPlaces(value, setFromSuggestions)
          }}
        />

        {activeSearch === 'from' && fromSuggestions.length > 0 && (
          <div className="place-suggestions">
            {fromSuggestions.map(place => {
              const [lon, lat] = place.geometry.coordinates

              return (
                <button
                  type="button"
                  key={place.id}
                  className="place-suggestion"
                  onClick={() => {
                    setFrom(place.place_name || place.text)

                    setJourney(prev => ({
                      ...prev,
                      from: place.place_name || place.text,
                      fromCoords: {
                        lat,
                        lon,
                      },
                    }))

                    setFromSuggestions([])
                    setActiveSearch(null)
                  }}
                >
                  <strong>{place.text}</strong>

                  <small>
                    {place.branchAddress || place.place_name}
                    {' · '}
                    {getDistanceKm(place).toFixed(1)} km away
                  </small>
                </button>
              )
            })}
          </div>
        )}
      </div>
      <span className="search-connector" aria-hidden="true">&darr;</span>
      <div
        className="place-field"
        style={{ position: 'relative' }}
      >
        <label htmlFor="to">TO</label>

        <input
          id="to"
          value={to}
          onFocus={() => setActiveSearch('to')}
          onChange={e => {
            const value = e.target.value
            setTo(value)

            setJourney(prev => ({
              ...prev,
              toCoords: null,
            }))

            searchPlaces(value, setToSuggestions)
          }}
        />

        {activeSearch === 'to' && toSuggestions.length > 0 && (
          <div className="place-suggestions">
            {toSuggestions.map(place => {
              const [lon, lat] = place.geometry.coordinates

              return (
                <button
                  type="button"
                  key={place.id}
                  className="place-suggestion"
                  onClick={() => {
                    setTo(place.place_name || place.text)

                    setJourney(prev => ({
                      ...prev,
                      to: place.place_name || place.text,
                      toCoords: {
                        lat,
                        lon,
                      },
                    }))

                    setToSuggestions([])
                    setActiveSearch(null)
                  }}
                >
                  <strong>{place.text}</strong>

                  <small>
                    {place.branchAddress || place.place_name}
                    {' · '}
                    {getDistanceKm(place).toFixed(1)} km away
                  </small>
                </button>
              )
            })}
          </div>
        )}
      </div>
      <button className="find-route" type="submit">Find safer route <span>&rarr;</span></button>
    </form>
    <aside className="route-panel">
      {loading && <div className="quiet-loading">Updating route <i /></div>}
      {error && (
        <div className="quiet-error">
          Route data unavailable
        </div>
      )}
      {data && <>
        <div className="recommendation">
          <p className="eyebrow">CHIRAAG RECOMMENDS</p>
          <div className="recommendation-title">
            Safer route
          </div>
          <div className="route-duration">
            {Math.round(data.chiraag_route.metrics.total_length_m)} m
          </div>

          <HeroMetric
            delta={{
              extra_m: data.evidence_summary.extra_distance_m,
              extra_pct:
                data.baseline_route.metrics.total_length_m > 0
                  ? (
                    (data.evidence_summary.extra_distance_m /
                      data.baseline_route.metrics.total_length_m) *
                    100
                  ).toFixed(1)
                  : 0,
              dark_avoided_m: data.evidence_summary.unlit_meters_avoided,
            }}
          />
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
