import sys
import os
import random
from shapely.geometry import LineString

# Ensure python can import from the 'app' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import SessionLocal, Base, engine
from app.models.road_segment import RoadSegment

def seed_test_ward():
    """Populates PostGIS with mock road network segments for testing."""
    print("Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Clean out existing test data
    db.query(RoadSegment).delete()
    db.commit()

    print("Seeding mock road network around test ward...")
    
    # Generate a simple grid of connected road segments (Lat/Lon around 28.6139, 77.2090)
    base_lat = 28.6139
    base_lon = 77.2090
    step = 0.002
    
    segments = []
    osm_id_counter = 1000
    
    # Create horizontal and vertical grid segments
    for i in range(4):
        for j in range(4):
            # Horizontal segment
            line_h = LineString([
                (base_lon + (j * step), base_lat + (i * step)),
                (base_lon + ((j + 1) * step), base_lat + (i * step))
            ])
            # Assign random dark fraction (some bright, some pitch black)
            dark_frac_h = round(random.choice([0.0, 0.2, 0.7, 0.95]), 2)
            
            segments.append(RoadSegment(
                osm_id=osm_id_counter,
                length_m=220.0,
                dark_fraction=dark_frac_h,
                longest_gap_m=dark_frac_h * 220.0,
                calibrated_lighting_prob=1.0 - dark_frac_h,
                observation_state="audited" if dark_frac_h > 0.5 else "predicted",
                geom=f"SRID=4326;{line_h.wkt}"
            ))
            osm_id_counter += 1
            
            # Vertical segment
            line_v = LineString([
                (base_lon + (j * step), base_lat + (i * step)),
                (base_lon + (j * step), base_lat + ((i + 1) * step))
            ])
            dark_frac_v = round(random.choice([0.1, 0.3, 0.8, 1.0]), 2)
            
            segments.append(RoadSegment(
                osm_id=osm_id_counter,
                length_m=220.0,
                dark_fraction=dark_frac_v,
                longest_gap_m=dark_frac_v * 220.0,
                calibrated_lighting_prob=1.0 - dark_frac_v,
                observation_state="predicted",
                geom=f"SRID=4326;{line_v.wkt}"
            ))
            osm_id_counter += 1

    db.add_all(segments)
    db.commit()
    db.close()
    
    print(f"Successfully seeded {len(segments)} road segments into PostGIS!")

if __name__ == "__main__":
    seed_test_ward()