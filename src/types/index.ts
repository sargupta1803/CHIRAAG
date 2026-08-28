export type Coordinates = [number, number]

export interface GeoJsonLine {
  type: 'Feature'
  properties: { seg_id?: number; status?: 'observed' | 'unknown' }
  geometry: { type: 'LineString'; coordinates: Coordinates[] }
}

export interface RouteData {
  geojson: GeoJsonLine
  length_m: number
  risk: number
  dark_m: number
  lambda?: number
}

export interface RouteDelta { extra_m: number; extra_pct: number; dark_avoided_m: number }

export interface SegmentScore {
  seg_id: number
  dark_fraction: number
  longest_gap_m: number
  is_unknown: boolean
  lights: number
  image_ids: string[]
}

export interface RouteResponse {
  shortest: RouteData
  safest: RouteData
  delta: RouteDelta
  segments: SegmentScore[]
}

export interface EvidenceData extends SegmentScore {
  coverage: number
  confidence: string
  captured_at: string
  cctv: boolean
  image: string
  risk: 'Low' | 'Medium' | 'High' | 'Unknown'
}

export type UnknownPolicy = 'avoid' | 'neutral' | 'show'
