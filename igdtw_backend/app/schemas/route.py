from pydantic import BaseModel, Field

class Location(BaseModel):
    lat: float = Field(..., example=28.6139, description="Latitude coordinate")
    lon: float = Field(..., example=77.2090, description="Longitude coordinate")

class RouteRequest(BaseModel):
    origin: Location
    destination: Location
    alpha: float = Field(
        default=1.20, 
        ge=1.0, 
        le=2.0, 
        description="Detour cap multiplier (e.g. 1.20 allows max 20% extra distance)"
    )

class PathMetrics(BaseModel):
    total_length_m: float
    unlit_length_m: float
    dark_fraction: float

class RouteOption(BaseModel):
    nodes: list[tuple[float, float]]  # List of (lon, lat) points for GeoJSON rendering
    metrics: PathMetrics

class EvidenceSummary(BaseModel):
    unlit_meters_avoided: float
    extra_distance_m: float
    safety_gain_percent: float

class RouteResponse(BaseModel):
    status: str
    detour_multiplier_cap: float
    baseline_route: RouteOption
    chiraag_route: RouteOption
    evidence_summary: EvidenceSummary