"""
pipeline/run_ingestion.py

One-off orchestrator that runs the full CHIRAAG data pipeline end-to-end:

  1. Pull street geometry from OpenStreetMap        -> road_segments
  2. Pull streetlight points from Mapillary          -> streetlights
  3. Snap each streetlight onto its nearest road
  4. Compute dark_fraction / longest_gap_m per road segment
  5. Write those scores back to road_segments

This is an OFFLINE batch job. The live API (app/) never imports or calls
this file -- it only reads whatever is already sitting in road_segments /
streetlights. Run this manually (or on a schedule) whenever you want to
(re)populate real data instead of the seed_ward.py mock grid.

Usage:
    python -m pipeline.run_ingestion \\
        --place "Connaught Place, New Delhi, India" \\
        --bbox "77.20,28.60,77.24,28.64" \\
        --mapillary-token YOUR_TOKEN

    # Re-score existing roads/lights without re-fetching from OSM/Mapillary:
    python -m pipeline.run_ingestion --skip-osm --skip-lights \\
        --bbox "" --mapillary-token ""
"""

import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import geopandas as gpd
from sqlalchemy import create_engine, text
import pandas as pd

from app.config import settings
from app.db import Base
import app.models
from pipeline.ingest_osmnx import ingest_osm
from pipeline.ingest_mapillary import ingest_mapillary
from pipeline.snap_to_road import snap_lights_to_roads
from pipeline.gap_analysis import calculate_segment_metrics


def load_roads(engine) -> gpd.GeoDataFrame:
    """Load road_segments as a GeoDataFrame with 'id' as a normal column
    (not the index) -- snap_to_road.py's join looks for an 'id' column on
    both sides and reads back 'id_right', so the index won't work here."""
    return gpd.read_postgis(
        "SELECT id, length_m, geom AS geometry FROM road_segments",
        engine,
        geom_col="geometry",
    )


def load_lights(engine) -> gpd.GeoDataFrame:
    return gpd.read_postgis(
        "SELECT id, geom AS geometry FROM streetlights",
        engine,
        geom_col="geometry",
    )


def score_and_write_segments(engine, roads_gdf: gpd.GeoDataFrame, lights_gdf: gpd.GeoDataFrame):
    """Snap lights to roads, compute dark_fraction/longest_gap_m per road,
    and UPDATE road_segments with the results."""

    if roads_gdf.empty:
        print("No road segments found -- nothing to score. Run OSM ingestion first.")
        return

    if lights_gdf.empty:
        print("No streetlights found -- leaving all segments unscored (fully dark by default).")
        snapped = {}
    else:
        snapped = snap_lights_to_roads(roads_gdf, lights_gdf)  # {road_id: [distances_along_road]}

    updates = []
    for _, road in roads_gdf.iterrows():
        road_id = road["id"]
        raw_length = road["length_m"]
        segment_length = float(raw_length) if pd.notna(raw_length) else 0.0
        light_positions = snapped.get(road_id, [])

        if light_positions:
            metrics = calculate_segment_metrics(
                segment_length,
                light_positions
            )

            updates.append({
                "id": road_id,
                "dark_fraction": metrics["dark_fraction"],
                "longest_gap_m": metrics["longest_gap_m"],
                "observation_state": "predicted",
            })

        else:
            # No streetlight evidence does NOT mean the road is dark.
            updates.append({
                "id": road_id,
                "dark_fraction": None,
                "longest_gap_m": None,
                "observation_state": "unobserved",
            })


    print(f"Writing scores for {len(updates)} road segments...")

    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE road_segments
                SET dark_fraction = :dark_fraction,
                    longest_gap_m = :longest_gap_m,
                    observation_state = :observation_state
                WHERE id = :id
            """),
            updates,
        )

    print("Done scoring segments.")


def main():
    parser = argparse.ArgumentParser(description="Run the CHIRAAG ingestion pipeline.")
    parser.add_argument("--place", default="Connaught Place, New Delhi, India",
                         help="Place name passed to OSMnx for street geometry. "
                              "Only works for places that resolve to a (Multi)Polygon "
                              "boundary -- landmarks/POIs will fail. Prefer --lat/--lon "
                              "for those instead.")
    parser.add_argument("--lat", type=float, default=None,
                         help="Center latitude for point-based OSM ingestion "
                              "(bypasses place-name geocoding entirely).")
    parser.add_argument("--lon", type=float, default=None,
                         help="Center longitude for point-based OSM ingestion.")
    parser.add_argument("--radius", type=float, default=1000,
                         help="Radius in meters around --lat/--lon to pull streets from. "
                              "Only used when --lat/--lon are given. Default: 1000.")
    parser.add_argument("--bbox", default="",
                         help="Mapillary bounding box as 'minLon,minLat,maxLon,maxLat'. "
                              "Required unless --skip-lights is set.")
    parser.add_argument("--mapillary-token", default="",
                         help="Mapillary API access token. Required unless --skip-lights is set.")
    parser.add_argument("--skip-osm", action="store_true",
                         help="Skip OSM street ingestion (use existing road_segments).")
    parser.add_argument("--skip-lights", action="store_true",
                         help="Skip Mapillary ingestion (use existing streetlights).")
    args = parser.parse_args()

    if not args.skip_lights and (not args.bbox or not args.mapillary_token):
        parser.error("--bbox and --mapillary-token are required unless --skip-lights is set.")

    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    if not args.skip_osm:
        if args.lat is not None and args.lon is not None:
            print(f"Ingesting OSM street network around ({args.lat}, {args.lon}), "
                  f"radius {args.radius}m...")
            ingest_osm(
                db_url=settings.DATABASE_URL,
                center_point=(args.lat, args.lon),
                dist=args.radius,
            )
        else:
            print(f"Ingesting OSM street network for '{args.place}'...")
            ingest_osm(place_name=args.place, db_url=settings.DATABASE_URL)
    else:
        print("Skipping OSM ingestion.")

    if not args.skip_lights:
        print(f"Ingesting Mapillary streetlights for bbox {args.bbox}...")
        ingest_mapillary(bbox=args.bbox, access_token=args.mapillary_token, db_url=settings.DATABASE_URL)
    else:
        print("Skipping Mapillary ingestion.")

    print("Loading roads and lights from PostGIS for scoring...")
    roads_gdf = load_roads(engine)
    lights_gdf = load_lights(engine)
    print(f"  {len(roads_gdf)} road segments, {len(lights_gdf)} streetlights loaded.")

    score_and_write_segments(engine, roads_gdf, lights_gdf)

    print("Pipeline complete.")



if __name__ == "__main__":
    main()