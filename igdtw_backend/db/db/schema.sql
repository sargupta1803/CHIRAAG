CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Scored Road Segments (Graph Edges)
CREATE TABLE road_segment(
    id SERIAL PRIMARY KEY,
    osm_id BIGINT UNIQUE,
    geom GEOMETRY(LineString, 4326),
    length_m FLOAT,
    dark_fraction FLOAT DEFAULT 0.0,
    longest_gap_m FLOAT DEFAULT 0.0,
    calibrated_lighting_prob FLOAT DEFAULT 0.5,
    observation_state VARCHAR(20) DEFAULT 'UNKNOWN'
);

-- 2. Streetlight Detections
CREATE TABLE streetlights (
    id SERIAL PRIMARY KEY,
    mapillary_id VARCHAR(100),
    geom GEOMETRY(Point, 4326)
);

-- 3. Human Ground Truth Night Audits
CREATE TABLE night_audits (
    id SERIAL PRIMARY KEY,
    segment_id INT REFERENCES road_segments(id),
    audit_score INT, -- e.g., 0-5 rating
    working_lights INT,
    audited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
