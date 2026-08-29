import { routeData } from '../data/routeData.js'

export function calculateRoute(hour, alpha, unknownPolicy) {
  const timeFactor = hour < 18 ? 0.18 : hour < 21 ? 0.62 : 1
  const detourFactor = Math.min(1, Math.max(0.15, alpha / 20))

  const data = structuredClone(routeData)

  data.delta.dark_avoided_m = Math.round(
    306 * timeFactor * detourFactor
  )

  data.delta.extra_m = Math.round(
    89 * detourFactor
  )

  data.delta.extra_pct = Math.round(
    (data.delta.extra_m / data.shortest.length_m) * 100
  )

  data.safest.length_m =
    data.shortest.length_m + data.delta.extra_m

  data.safest.dark_m =
    Math.round(
      data.shortest.dark_m - data.delta.dark_avoided_m
    )

  if (unknownPolicy === 'avoid') {
    data.safest.length_m += 24
  }

  return data
}