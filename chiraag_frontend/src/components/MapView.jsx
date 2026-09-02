import React, { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'


const API_KEY = import.meta.env.VITE_MAPTILER_KEY

const STREET_STYLE =
  `https://api.maptiler.com/maps/streets-v4/style.json?key=${API_KEY}`

const SATELLITE_STYLE =
  `https://api.maptiler.com/maps/satellite/style.json?key=${API_KEY}`




const line = (route) => ({
  type: 'FeatureCollection',
  features: [route],
})

export function MapView({
  data,
  selected,
  selectedSegment,
  onSegment,
  fromCoords,
  toCoords,
  fromName,
  toName,
}) {
  const container = useRef(null)
  const map = useRef(null)
  const markers = useRef([])
  const [satellite, setSatellite] = useState(false)

  function addChiraagLayers(m) {
    if (!m.getSource('shortest')) {
      m.addSource('shortest', {
        type: 'geojson',
        data: line({
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: data.baseline_route.nodes,
          },
        }),
      })

      m.addLayer({
        id: 'shortest-line',
        type: 'line',
        source: 'shortest',
        paint: {
          'line-color': '#575b58',
          'line-width': selected === 'shortest' ? 6 : 3.5,
          'line-opacity': selected === 'shortest' ? 0.92 : 0.64,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      })
    }

    if (!m.getSource('safest')) {
      m.addSource('safest', {
        type: 'geojson',
        data: line({
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: data.chiraag_route.nodes,
          },
        }),
      })

      m.addLayer({
        id: 'safest-line',
        type: 'line',
        source: 'safest',
        paint: {
          'line-color': '#ad7f24',
          'line-width': selected === 'safe' ? 7 : 4.5,
          'line-opacity': selected === 'safe' ? 1 : 0.72,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      })
    }


  }

  function addMarkers(m) {
    markers.current.forEach(marker => marker.remove())
    markers.current = []

    const points = [
      {
        coords: [fromCoords.lon, fromCoords.lat],
        color: '#222522',
        popup: fromName,
      },
      {
        coords: [toCoords.lon, toCoords.lat],
        color: '#ad7f24',
        popup: toName,
      },
    ]

    points.forEach(point => {
      const marker = new maplibregl.Marker({
        color: point.color,
      })
        .setLngLat(point.coords)
        .setPopup(
          new maplibregl.Popup({ offset: 22 }).setText(point.popup)
        )
        .addTo(m)

      markers.current.push(marker)
    })
  }

  useEffect(() => {
    if (!container.current || map.current) return

    const m = new maplibregl.Map({
      container: container.current,
      style: STREET_STYLE,
      center: [77.2194, 28.6302],
      zoom: 15.65,
      attributionControl: false,
      pitchWithRotate: false,
      dragRotate: false,
    })

    m.addControl(
      new maplibregl.NavigationControl({
        showCompass: false,
      }),
      'top-right'
    )

    map.current = m

    m.on('load', () => {
      addChiraagLayers(m)
      addMarkers(m)

      const coords = [
        ...data.baseline_route.nodes,
        ...data.chiraag_route.nodes,
      ]

      const bounds = coords.reduce(
        (b, coord) => b.extend(coord),
        new maplibregl.LngLatBounds(coords[0], coords[0])
      )

      m.fitBounds(bounds, {
        padding: 100,
        duration: 0,
      })


    })

    return () => {
      markers.current.forEach(marker => marker.remove())
      markers.current = []
      m.remove()
      map.current = null
    }
  }, [])

  useEffect(() => {
    const m = map.current

    if (!m || !m.isStyleLoaded()) return

    const shortestSource = m.getSource('shortest')
    const safestSource = m.getSource('safest')

    shortestSource?.setData(
      line({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: data.baseline_route.nodes,
        },
      })
    )

    safestSource?.setData(
      line({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: data.chiraag_route.nodes,
        },
      })
    )

    m.setPaintProperty(
      'shortest-line',
      'line-width',
      selected === 'shortest' ? 6 : 3.5
    )

    m.setPaintProperty(
      'shortest-line',
      'line-opacity',
      selected === 'shortest' ? 0.92 : 0.64
    )

    m.setPaintProperty(
      'safest-line',
      'line-width',
      selected === 'safe' ? 7 : 4.5
    )

    m.setPaintProperty(
      'safest-line',
      'line-opacity',
      selected === 'safe' ? 1 : 0.72
    )
  }, [data, selected])



  function switchStyle() {
    const m = map.current

    if (!m) return

    const nextSatellite = !satellite

    setSatellite(nextSatellite)

    m.once('style.load', () => {
      addChiraagLayers(m)
      addMarkers(m)


    })

    m.setStyle(
      nextSatellite
        ? SATELLITE_STYLE
        : STREET_STYLE
    )
  }

  return (
    <div ref={container} className="map-canvas">
      <div className="route-chip">
        <i className={selected === 'safe' ? 'gold' : 'grey'} />

        {selected === 'safe'
          ? 'Safer route selected'
          : 'Shortest route selected'}
      </div>

      <div
        style={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 10,
          display: 'flex',
          gap: 6,
          background: 'rgba(255,255,255,0.96)',
          padding: 4,
          borderRadius: 8,
          boxShadow: '0 2px 10px rgba(0,0,0,0.14)',
        }}
      >
        <button
          type="button"
          onClick={() => {
            if (satellite) switchStyle()
          }}
          style={{
            border: 'none',
            borderRadius: 6,
            padding: '7px 11px',
            background: !satellite ? '#222522' : 'transparent',
            color: !satellite ? '#fff' : '#222522',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Map
        </button>

        <button
          type="button"
          onClick={() => {
            if (!satellite) switchStyle()
          }}
          style={{
            border: 'none',
            borderRadius: 6,
            padding: '7px 11px',
            background: satellite ? '#222522' : 'transparent',
            color: satellite ? '#fff' : '#222522',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Satellite
        </button>
      </div>

      <div className="map-legend">
        <span>
          <i className="legend-safe" /> Safer
        </span>

        <span>
          <i className="legend-short" /> Shortest
        </span>

        <span>
          <i className="legend-unknown" /> Limited observation
        </span>
      </div>

      <div className="map-attribution">
        © OpenStreetMap contributors &nbsp; | &nbsp; © MapTiler
      </div>
    </div>
  )
}