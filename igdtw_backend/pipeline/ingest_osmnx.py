import osmnx as ox
import geopandas as gpd
from sqlalchemy import create_engine, text

STAGING_TABLE = "_incoming_road_segments"


def _ensure_schema(engine):
    """
    Create the real tables from the ORM models if they don't exist yet.

    Without this, to_postgis would create road_segments from the GeoDataFrame
    alone -- osm_id, length_m and geom only, with no id, dark_fraction,
    longest_gap_m, calibrated_lighting_prob, observation_state or created_at.
    Base.metadata.create_all() only creates missing *tables*, never missing
    columns, so a stunted table would survive every later API start and break
    scoring and routing in confusing ways.
    """
    from app.db import Base
    import app.models  # noqa: F401  -- registers the models on Base.metadata

    Base.metadata.create_all(bind=engine)


def ingest_osm(
    place_name="Piedmont, California, USA",
    db_url="postgresql://user:pass@localhost:5432/chiraag",
    center_point=None,   # optional (lat, lon) tuple -- bypasses place-name geocoding
    dist=1000,           # radius in meters, only used when center_point is given
):
    """
    Pulls a walking street network from OSM and writes it into road_segments.

    Safe to re-run: segments already present are skipped rather than appended
    a second time. Deduplication happens in PostGIS via ST_Equals, which is
    direction-agnostic, so a street stored A->B matches an incoming B->A.

    Two modes:
      - place_name: looks up an administrative/neighborhood boundary by name.
        NOTE: this only works for places Nominatim resolves to a (Multi)Polygon
        -- landmarks / POIs (e.g. "Connaught Place") resolve to a single Point
        and will raise a TypeError. Use center_point instead for those.
      - center_point=(lat, lon): draws a square network of side 2*dist metres
        around an exact coordinate. Always works regardless of how Nominatim
        classifies the location.
    """
    if center_point is not None:
        G = ox.graph_from_point(center_point, dist=dist, network_type="walk")
    else:
        G = ox.graph_from_place(place_name, network_type="walk")

    _, gdf_edges = ox.graph_to_gdfs(G)

    gdf_edges = gdf_edges.reset_index()

    # OSMnx emits reciprocal edges for walk networks (u->v and v->u are the
    # same physical street). Keep one row per undirected pair, or lights get
    # split arbitrarily between the twins at snap time.
    #
    # Partitioning on (_pair, key) rather than _pair alone matters: reciprocal
    # twins share key 0, while genuine parallel streets between the same two
    # junctions get keys 0 and 1 and must both survive.
    gdf_edges["_pair"] = [
        tuple(sorted(pair)) for pair in zip(gdf_edges["u"], gdf_edges["v"])
    ]
    gdf_edges = gdf_edges.drop_duplicates(subset=["_pair", "key"])
    gdf_edges = gdf_edges.drop(columns=["_pair"])

    edges = gdf_edges[['geometry', 'length', 'osmid']].copy()

    # osmid can be a list when multiple OSM ways got merged into one graph edge
    edges['osmid'] = edges['osmid'].apply(lambda x: x[0] if isinstance(x, list) else x)

    edges = edges.rename(columns={'length': 'length_m', 'osmid': 'osm_id'})
    edges = edges.rename_geometry('geom')

    print(f"  OSM returned {len(edges)} unique street segments.")

    engine = create_engine(db_url)

    _ensure_schema(engine)

    # Stage the incoming batch, then insert only what PostGIS says is new.
    # Doing the comparison in the database avoids relying on Shapely and
    # PostGIS producing byte-identical WKB.
    edges.to_postgis(STAGING_TABLE, engine, if_exists='replace', index=False)

    try:
        with engine.begin() as conn:
            existing_before = conn.execute(
                text("SELECT count(*) FROM road_segments")
            ).scalar()

            inserted = conn.execute(text(f"""
                INSERT INTO road_segments (osm_id, length_m, geom, observation_state)
                SELECT i.osm_id, i.length_m, i.geom, 'unobserved'
                FROM {STAGING_TABLE} AS i
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM road_segments AS r
                    WHERE r.geom && i.geom
                      AND ST_Equals(r.geom, i.geom)
                )
            """)).rowcount

            skipped = len(edges) - inserted

            print(
                f"  {existing_before} segments already in the database. "
                f"Inserted {inserted} new, skipped {skipped} duplicates."
            )

    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {STAGING_TABLE}"))


# this file takes in the raw osmx data.
# takes place name (or a center point + radius) and the db as parameters
# and writes the data into postgres