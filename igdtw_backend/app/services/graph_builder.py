import networkx as nx
import shapely.wkb
from sqlalchemy import text


def build_graph_from_db(db_session) -> nx.MultiDiGraph:
    """
    Fetch scored road segments from PostGIS and build a NetworkX graph.
    Unknown safety evidence is preserved as NULL instead of being treated
    as fully lit.
    """
    G = nx.MultiDiGraph()

    query = text("""
        SELECT
            id,
            osm_id,
            length_m,
            dark_fraction,
            longest_gap_m,
            calibrated_lighting_prob,
            observation_state,
            ST_AsBinary(geom) AS geom_wkb
        FROM road_segments
    """)

    result = db_session.execute(query).fetchall()

    for row in result:
        line_geom = shapely.wkb.loads(bytes(row.geom_wkb))
        coords = list(line_geom.coords)

        if len(coords) < 2:
            continue

        start_node = coords[0]
        end_node = coords[-1]

        G.add_edge(
            start_node,
            end_node,
            id=row.id,
            osm_id=row.osm_id,
            length_m=float(row.length_m or 0.0),

            # IMPORTANT:
            # Preserve NULL so routing can distinguish unknown
            # from known dark.
            dark_fraction=(
                float(row.dark_fraction)
                if row.dark_fraction is not None
                else None
            ),

            longest_gap_m=(
                float(row.longest_gap_m)
                if row.longest_gap_m is not None
                else None
            ),

            calibrated_prob=(
                float(row.calibrated_lighting_prob)
                if row.calibrated_lighting_prob is not None
                else 0.5
            ),

            observation_state=row.observation_state,
            geometry=line_geom
        )

    return G