const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const USE_MOCK_DATA = false

export async function getRoute(
  hour,
  detour,
  unknownPolicy,
  fromCoords,
  toCoords
) {
  if (!fromCoords || !toCoords) {
    throw new Error('Origin and destination coordinates are required')
  }

  const alpha = 1 + Number(detour) / 100

  const response = await fetch(`${BASE_URL}/api/v1/route`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      origin: {
        lat: fromCoords.lat,
        lon: fromCoords.lon,
      },
      destination: {
        lat: toCoords.lat,
        lon: toCoords.lon,
      },
      alpha,
      unknown_policy: unknownPolicy,
    }),
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || 'Route data unavailable')
  }

  return response.json()
}

export async function getSegment(id) {
  const response = await fetch(
    `${BASE_URL}/api/v1/evidence/segment/${id}`
  )

  if (!response.ok) {
    throw new Error('Segment data unavailable')
  }

  return response.json()
}