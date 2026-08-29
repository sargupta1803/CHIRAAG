import { routeData, routeCandidates } from '../data/routeData.js'
import { calculateRouteRisk } from './safetyService.js'

export function calculateRoute(hour, alpha, unknownPolicy) {
  const data = structuredClone(routeData)

  const scoredSegments = data.segments.map(segment => ({
    ...segment,
    risk: segment.is_unknown
      ? null
      : calculateRouteRisk([segment], unknownPolicy).risk
  }))

  const getRouteSegments = candidate =>
    candidate.segment_ids
      .map(id =>
        scoredSegments.find(segment => segment.seg_id === id)
      )
      .filter(Boolean)

  const scoredRoutes = routeCandidates.map(candidate => {
    const segments = getRouteSegments(candidate)

    const riskResult = calculateRouteRisk(
      segments,
      unknownPolicy
    )

    const baseRoute =
      candidate.id === 'shortest'
        ? data.shortest
        : data.safest

    const extraDistance =
      baseRoute.length_m - data.shortest.length_m

    const detourPct =
      (extraDistance / data.shortest.length_m) * 100

    const withinDetourLimit = detourPct <= alpha

    const routeScore =
      riskResult.risk === null
        ? Infinity
        : riskResult.risk + (detourPct / 100) * 0.5

    return {
      ...candidate,
      segments,
      risk: riskResult.risk,
      detourPct,
      withinDetourLimit,
      routeScore
    }
  })

  const eligibleRoutes = scoredRoutes.filter(
    route => route.withinDetourLimit
  )

  const bestRoute =
    eligibleRoutes.length > 0
      ? eligibleRoutes.reduce((best, route) =>
          route.routeScore < best.routeScore
            ? route
            : best
        )
      : scoredRoutes.find(route => route.id === 'shortest')

  data.shortest.risk =
    scoredRoutes.find(route => route.id === 'shortest')?.risk ?? null

  data.safest.risk =
    scoredRoutes.find(route => route.id === 'safer')?.risk ?? null

  data.recommended_route = bestRoute?.id ?? 'shortest'

  data.segments = scoredSegments

  const timeFactor =
    hour < 18 ? 0.18 :
    hour < 21 ? 0.62 :
    1

  const detourFactor = Math.min(
    1,
    Math.max(0.15, alpha / 20)
  )

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

  data.safest.dark_m = Math.max(
    0,
    Math.round(
      data.shortest.dark_m -
      data.delta.dark_avoided_m
    )
  )

  if (unknownPolicy === 'avoid') {
    data.safest.length_m += 24
  }

  return data
}