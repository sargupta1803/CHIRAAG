import fixture from '../fixtures/route.json'
import { evidence } from '../fixtures/evidence'

export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA !== 'false'
const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export async function getRoute(hour, alpha, unknownPolicy, from = 'Connaught Place', to = 'India Gate') {
  if (USE_MOCK_DATA) {
    const timeFactor = hour < 18 ? 0.18 : hour < 21 ? 0.62 : 1
    const detourFactor = Math.min(1, Math.max(0.15, alpha / 20))
    const data = structuredClone(fixture)
    data.delta.dark_avoided_m = Math.round(306 * timeFactor * detourFactor)
    data.delta.extra_m = Math.round(89 * detourFactor)
    data.delta.extra_pct = Math.round((data.delta.extra_m / data.shortest.length_m) * 100)
    data.safest.length_m = data.shortest.length_m + data.delta.extra_m
    data.safest.dark_m = Math.round(data.shortest.dark_m - data.delta.dark_avoided_m)
    if (unknownPolicy === 'avoid') data.safest.length_m += 24
    return data
  }
  const params = new URLSearchParams({ from, to, hour: String(hour), alpha: String(alpha), unknown_policy: unknownPolicy })
  const response = await fetch(`${BASE_URL}/route?${params}`)
  if (!response.ok) throw new Error('Route data unavailable')
  return response.json()
}

export async function getSegment(id) {
  if (USE_MOCK_DATA) return evidence[id]
  const response = await fetch(`${BASE_URL}/segment/${id}`)
  if (!response.ok) throw new Error('Segment data unavailable')
  return response.json()
}
