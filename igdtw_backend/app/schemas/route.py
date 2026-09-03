from pydantic import BaseModel, Field

class Location(BaseModel):
    lat: float = Field(..., json_schema_extra={"example": 28.6139}, description="Latitude coordinate")
    lon: float = Field(..., json_schema_extra={"example": 77.2090}, description="Longitude coordinate")

class RouteRequest(BaseModel):
    origin: Location
    destination: Location

    alpha: float = Field(
        default=1.20,
        ge=1.0,
        le=2.0,
        description="Maximum allowed detour multiplier"
    )

    unknown_policy: str = Field(
        default="neutral",
        pattern="^(avoid|neutral|show_gaps)$",
        description="How to handle road segments with insufficient safety evidence"
    )

class PathMetrics(BaseModel):
    total_length_m: float
    unlit_length_m: float
    unknown_length_m: float
    dark_fraction: float
    coverage_ratio: float

class RouteSegment(BaseModel):
    """
    One physical street along the route, with its own geometry and evidence.

    This is what lets the map draw streets individually (coloured by
    observation state) and attach a click handler that opens the evidence
    drawer for that road_id.
    """
    road_id: int | None = None
    length_m: float

    # NULL for unobserved streets. Never coerce to 0.0 -- "no evidence"
    # is not "no darkness".
    dark_fraction: float | None = None

    observation_state: str
    coordinates: list[tuple[float, float]]  # (lon, lat) points for this street

class RouteOption(BaseModel):
    nodes: list[tuple[float, float]]  # flattened (lon, lat) polyline for the whole route
    segments: list[RouteSegment] = []  # per-street breakdown; empty is valid
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