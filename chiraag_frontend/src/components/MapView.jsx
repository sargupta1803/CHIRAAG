import React, { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'


const API_KEY = import.meta.env.VITE_MAPTILER_KEY

const STREET_STYLE =
  `https://api.maptiler.com/maps/streets-v4/style.json?key=${API_KEY}`

const SATELLITE_STYLE =
  `https://api.maptiler.com/maps/satellite/style.json?key=${API_KEY}`

const SEGMENTS = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { seg_id: 4412, status: 'observed' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [77.2186, 28.6317],
          [77.2201, 28.6306],
          [77.2212, 28.6286],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { seg_id: 4413, status: 'observed' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [77.2168, 28.6328],
          [77.2186, 28.6317],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { seg_id: 4414, status: 'unknown' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [77.2161, 28.6313],
          [77.2173, 28.6296],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { seg_id: 4415, status: 'observed' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [77.2173, 28.6296],
          [77.2195, 28.6290],
          [77.2212, 28.6286],
        ],
      },
    },
  ],
}

const OBSERVATIONS = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'Point',
        coordinates: [77.2174, 28.6298],
      },
    },
    {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'Point',
        coordinates: [77.2195, 28.6290],
      },
    },
    {
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'Point',
        coordinates: [77.2210, 28.6287],
      },
    },
  ],
}

const line = (route) => ({
  type: 'FeatureCollection',
  features: [route],
})

export function MapView({
  data,
  selected,
  selectedSegment,
  onSegment,
}) {
  const container = useRef(null)
  const map = useRef(null)
  const markers = useRef([])
  const [satellite, setSatellite] = useState(false)

  function addChiraagLayers(m) {
    if (!m.getSource('shortest')) {
      m.addSource('shortest', {
        type: 'geojson',
        data: line(data.shortest.geojson),
      })

      m.addLayer({
        id: 'shortest-line',
        type: 'line',
        source: 'shortest',
        paint: {
          'line-color': '#575b58',
          'line-width': selected === 'short' ? 6 : 3.5,
          'line-opacity': selected === 'short' ? 0.92 : 0.64,
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
        data: line(data.safest.geojson),
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

    if (!m.getSource('segments')) {
      m.addSource('segments', {
        type: 'geojson',
        data: SEGMENTS,
      })

      m.addLayer({
        id: 'unknown-segments',
        type: 'line',
        source: 'segments',
        filter: ['==', ['get', 'status'], 'unknown'],
        paint: {
          'line-color': '#6e746e',
          'line-width': 4,
          'line-dasharray': [1.4, 1.4],
          'line-opacity': 0.95,
        },
        layout: {
          'line-cap': 'round',
        },
      })

      m.addLayer({
        id: 'segment-hit',
        type: 'line',
        source: 'segments',
        paint: {
          'line-color': '#000',
          'line-opacity': 0,
          'line-width': 18,
        },
      })
    }

    if (!m.getSource('observations')) {
      m.addSource('observations', {
        type: 'geojson',
        data: OBSERVATIONS,
      })

      m.addLayer({
        id: 'observations',
        type: 'circle',
        source: 'observations',
        paint: {
          'circle-radius': 4,
          'circle-color': '#f9f6ed',
          'circle-stroke-color': '#77836f',
          'circle-stroke-width': 2,
        },
      })
    }

    if (!m.getSource('selected-segment')) {
      m.addSource('selected-segment', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      })

      m.addLayer({
        id: 'selected-line',
        type: 'line',
        source: 'selected-segment',
        paint: {
          'line-color': '#b84731',
          'line-width': 7,
          'line-opacity': 0.95,
        },
        layout: {
          'line-cap': 'round',
        },
      })
    }
  }

  function addMarkers(m) {
    markers.current.forEach(marker => marker.remove())
    markers.current = []

    const points = [
      {
        coords: [77.2168, 28.6328],
        color: '#222522',
        popup: 'Connaught Place',
      },
      {
        coords: [77.2233, 28.6272],
        color: '#ad7f24',
        popup: 'India Gate',
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
        ...data.shortest.geojson.geometry.coordinates,
        ...data.safest.geojson.geometry.coordinates,
      ]

      const bounds = coords.reduce(
        (b, coord) => b.extend(coord),
        new maplibregl.LngLatBounds(coords[0], coords[0])
      )

      m.fitBounds(bounds, {
        padding: 100,
        duration: 0,
      })

      m.on('mouseenter', 'segment-hit', () => {
        m.getCanvas().style.cursor = 'pointer'
      })

      m.on('mouseleave', 'segment-hit', () => {
        m.getCanvas().style.cursor = ''
      })

      m.on('click', 'segment-hit', event => {
        const id = event.features?.[0]?.properties?.seg_id

        if (id) {
          onSegment(Number(id))
        }
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

    shortestSource?.setData(line(data.shortest.geojson))
    safestSource?.setData(line(data.safest.geojson))

    m.setPaintProperty(
      'shortest-line',
      'line-width',
      selected === 'short' ? 6 : 3.5
    )

    m.setPaintProperty(
      'shortest-line',
      'line-opacity',
      selected === 'short' ? 0.92 : 0.64
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

  useEffect(() => {
    const m = map.current

    if (!m?.isStyleLoaded()) return

    const feature = SEGMENTS.features.find(
      f => f.properties.seg_id === selectedSegment
    )

    m.getSource('selected-segment')?.setData({
      type: 'FeatureCollection',
      features: feature ? [feature] : [],
    })
  }, [selectedSegment])

  function switchStyle() {
    const m = map.current

    if (!m) return

    const nextSatellite = !satellite

    setSatellite(nextSatellite)

    m.once('style.load', () => {
      addChiraagLayers(m)
      addMarkers(m)

      const feature = SEGMENTS.features.find(
        f => f.properties.seg_id === selectedSegment
      )

      m.getSource('selected-segment')?.setData({
        type: 'FeatureCollection',
        features: feature ? [feature] : [],
      })

      m.on('mouseenter', 'segment-hit', () => {
        m.getCanvas().style.cursor = 'pointer'
      })

      m.on('mouseleave', 'segment-hit', () => {
        m.getCanvas().style.cursor = ''
      })

      m.on('click', 'segment-hit', event => {
        const id = event.features?.[0]?.properties?.seg_id

        if (id) {
          onSegment(Number(id))
        }
      })
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