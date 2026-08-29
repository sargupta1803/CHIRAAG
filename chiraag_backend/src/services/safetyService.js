export function calculateSegmentRisk(segment) {
  if (segment.is_unknown) {
    return null
  }

  const darknessRisk = segment.dark_fraction

  const gapRisk = Math.min(
    segment.longest_gap_m / 200,
    1
  )

  const lightingRisk = Math.max(
    0,
    1 - segment.lights / 5
  )

  const risk =
    darknessRisk * 0.5 +
    gapRisk * 0.3 +
    lightingRisk * 0.2

  return Number(risk.toFixed(3))
}
export function calculateRouteRisk(segments, unknownPolicy = 'neutral') {
  const scoredSegments = segments.map(segment => ({
    ...segment,
    risk: calculateSegmentRisk(segment)
  }))

  const knownSegments = scoredSegments.filter(
    segment => segment.risk !== null
  )

  const unknownSegments = scoredSegments.filter(
    segment => segment.risk === null
  )

  if (
    unknownPolicy === 'avoid' &&
    unknownSegments.length > 0
  ) {
    return {
      risk: 1,
      segments: scoredSegments
    }
  }

  if (knownSegments.length === 0) {
    return {
      risk: null,
      segments: scoredSegments
    }
  }

  const totalRisk = knownSegments.reduce(
    (sum, segment) => sum + segment.risk,
    0
  )

  let risk = totalRisk / knownSegments.length

  if (
    unknownPolicy === 'show' &&
    unknownSegments.length > 0
  ) {
    risk = Math.min(1, risk + 0.1)
  }

  return {
    risk: Number(risk.toFixed(3)),
    segments: scoredSegments
  }
}