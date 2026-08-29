import { routeData } from '../data/routeData.js'
import { calculateRouteRisk } from './safetyService.js'

async function geocode(place) {
    const url = `https://api.maptiler.com/geocoding/${encodeURIComponent(`${place}, New Delhi`)}.json?key=${process.env.MAPTILER_API_KEY}&country=in&proximity=77.2295,28.6129&limit=1`

    const response = await fetch(url)

    if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Geocoding failed: ${response.status} ${errorText}`)
    }

    const data = await response.json()

    if (!data.features?.length) {
        throw new Error(`Location not found: ${place}`)
    }

    const [lon, lat] = data.features[0].geometry.coordinates

    return { lon, lat }
}

async function getWalkingRoutes(from, to) {
    const url =
        `https://router.project-osrm.org/route/v1/foot/` +
        `${from.lon},${from.lat};${to.lon},${to.lat}` +
        `?overview=full&geometries=geojson&steps=true&alternatives=true`

    const response = await fetch(url)

    if (!response.ok) {
        throw new Error('Routing failed')
    }

    const data = await response.json()

    if (data.code !== 'Ok' || !data.routes?.length) {
        throw new Error('No walking route found')
    }

    return data.routes
}

function getRouteSafety(route, segments, unknownPolicy) {
    const routeCoords = route.geometry.coordinates

    const matchedSegments = segments.filter(segment => {
        if (!segment.geometry?.coordinates) return false

        const segmentCoords = segment.geometry.coordinates

        return segmentCoords.some(([lon, lat]) =>
            routeCoords.some(([rLon, rLat]) => {
                const dx = (lon - rLon) * 111320
                const dy = (lat - rLat) * 111320

                return Math.sqrt(dx * dx + dy * dy) < 50
            })
        )
    })

    if (matchedSegments.length === 0) {
        return {
            risk: null,
            segments: []
        }
    }

    return calculateRouteRisk(
        matchedSegments,
        unknownPolicy
    )
}

export async function calculateRoute(
    hour,
    alpha,
    unknownPolicy,
    from = 'Connaught Place',
    to = 'India Gate'
) {
    const [fromCoord, toCoord] = await Promise.all([
        geocode(from),
        geocode(to)
    ])

    console.log('FROM:', from, fromCoord)
    console.log('TO:', to, toCoord)

    const walkingRoutes = await getWalkingRoutes(fromCoord, toCoord)

    console.log(
        'ROUTES FOUND:',
        walkingRoutes.length,
        walkingRoutes.map(route => Math.round(route.distance))
    )


    const data = structuredClone(routeData)

    const routeSafeties = walkingRoutes.map(route =>
        getRouteSafety(
            route,
            routeData.segments,
            unknownPolicy
        )
    )

    console.log(
        'ROUTE RISKS:',
        routeSafeties.map(safety => safety.risk)
    )


    const shortestRoute = walkingRoutes[0]

    const maxAllowedDistance =
        shortestRoute.distance * (1 + alpha / 100)

    const eligibleIndexes = walkingRoutes
        .map((route, index) => ({
            route,
            index
        }))
        .filter(({ route }) =>
            route.distance <= maxAllowedDistance
        )

    const safestEligible = eligibleIndexes.reduce(
        (best, current) => {
            const currentRisk = routeSafeties[current.index].risk
            const bestRisk = routeSafeties[best.index].risk

            if (currentRisk === null) return best
            if (bestRisk === null) return current

            return currentRisk < bestRisk
                ? current
                : best
        },
        eligibleIndexes[0] || {
            route: shortestRoute,
            index: 0
        }
    )

    const alternativeRoute = safestEligible.route
    const safestIndex = safestEligible.index

    data.shortest.geojson = shortestRoute.geometry
    data.shortest.length_m = Math.round(shortestRoute.distance)
    data.shortest.duration_s = Math.round(shortestRoute.duration)

    data.safest.geojson = alternativeRoute.geometry
    data.safest.length_m = Math.round(alternativeRoute.distance)
    data.safest.duration_s = Math.round(alternativeRoute.duration)


    const shortestDistance = shortestRoute.distance
    const safestDistance = alternativeRoute.distance

    data.delta = {
        extra_m: Math.round(alternativeRoute.distance - shortestRoute.distance),
        extra_pct: Number(
            (((alternativeRoute.distance - shortestRoute.distance) / shortestRoute.distance) * 100).toFixed(1)
        ),
        dark_avoided_m: 0
    }

    data.alternatives = walkingRoutes.map((route, index) => ({
        index,
        distance_m: Math.round(route.distance),
        duration_s: Math.round(route.duration),
        geojson: route.geometry
    }))

    data.segments = routeSafeties[safestIndex].segments

    if (routeSafeties[0].risk !== null) {
        data.shortest.risk = routeSafeties[0].risk
    }

    if (routeSafeties[safestIndex].risk !== null) {
        data.safest.risk = routeSafeties[safestIndex].risk
    }

    return data
}