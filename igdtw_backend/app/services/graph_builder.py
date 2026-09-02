import networkx as nx
import shapely.wkb
from sqlalchemy import text

def build_graph_from_db(db_session) -> nx.MultiDiGraph:
    """
    Fetches scored road segments from PostGIS and constructs an in-memory 
    NetworkX MultiDiGraph ready for lambda-sweep Dijkstra routing.
    """
    G = nx.MultiDiGraph()
    
    # Query scored road segments from PostGIS
    query = text("""
        SELECT id, osm_id, length_m, dark_fraction, longest_gap_m, 
               calibrated_lighting_prob, observation_state, ST_AsBinary(geom) as geom_wkb
        FROM road_segments
    """)
    result = db_session.execute(query).fetchall()
    
    for row in result:
        # Deserialize LineString geometry
        line_geom = shapely.wkb.loads(bytes(row.geom_wkb))
        coords = list(line_geom.coords)
        
        start_node = coords[0]   # (lon, lat)
        end_node = coords[-1]    # (lon, lat)
        
        # Add edge to graph with key scoring attributes
        G.add_edge(
            start_node,
            end_node,
            id=row.id,
            osm_id=row.osm_id,
            length_m=float(row.length_m or 0.0),
            dark_fraction=float(row.dark_fraction or 0.0),
            longest_gap_m=float(row.longest_gap_m or 0.0),
            calibrated_prob=float(row.calibrated_lighting_prob or 0.5),
            observation_state=row.observation_state,
            geometry=line_geom
        )
        
    return G