from pydantic import BaseModel

class SegmentEvidence(BaseModel):
    road_id: int
    length_m: float
    dark_fraction: float
    longest_gap_m: float
    calibrated_lighting_prob: float
    observation_state: str

class AuditSubmission(BaseModel):
    road_segment_id: int
    rating: float  # 0.0 to 5.0 rating scale
    observed_light_count: int