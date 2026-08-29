
import { calculateRoute } from '../services/routeService.js'

export function getRoute(req, res) {
  try {
    const {
      from = 'Connaught Place',
      to = 'India Gate',
      hour = '23',
      alpha = '20',
      unknown_policy = 'neutral'
    } = req.query

    const route = calculateRoute(
      Number(hour),
      Number(alpha),
      unknown_policy
    )

    res.json({
      ...route,
      from,
      to
    })
  } catch (error) {
    console.error('Route calculation failed:', error)

    res.status(500).json({
      error: 'Route data unavailable'
    })
  }
}