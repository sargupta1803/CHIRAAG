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

async function getWalkingRoute(from, to) {
    const url =
        `https://router.project-osrm.org/route/v1/driving/` +
        `${from.lon},${from.lat};${to.lon},${to.lat}` +
        `?overview=full&geometries=geojson&steps=true`

    const response = await fetch(url)

    if (!response.ok) {
        throw new Error(`Routing failed: ${response.status}`)
    }

    const data = await response.json()

    if (data.code !== 'Ok' || !data.routes?.length) {
        throw new Error('No route found')
    }

    return data.routes[0]
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

    const walkingRoute = await getWalkingRoute(fromCoord, toCoord)

    const safety = calculateRouteRisk(
        routeData.segments,
        unknownPolicy
    )

    const data = structuredClone(routeData)

    data.shortest.geojson = walkingRoute.geometry
    data.shortest.length_m = Math.round(walkingRoute.distance)

    data.safest.geojson = walkingRoute.geometry
    data.safest.length_m = Math.round(walkingRoute.distance)

    data.shortest.duration_s = Math.round(walkingRoute.duration)
    data.safest.duration_s = Math.round(walkingRoute.duration)

    data.segments = safety.segments

    if (safety.risk !== null) {
        data.shortest.risk = safety.risk
        data.safest.risk = safety.risk
    }

    return data
}