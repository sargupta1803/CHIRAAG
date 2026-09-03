import osmnx as ox
from sqlalchemy import create_engine
import geopandas as gpd

def ingest_osm(
    place_name="Piedmont, California, USA",
    db_url="postgresql://user:pass@localhost:5432/chiraag",
    center_point=None,   # optional (lat, lon) tuple -- bypasses place-name geocoding
    dist=1000,           # radius in meters, only used when center_point is given
):
    """
    Pulls a walking street network from OSM and writes it into road_segments.

    Two modes:
      - place_name: looks up an administrative/neighborhood boundary by name.
        NOTE: this only works for places Nominatim resolves to a (Multi)Polygon
        -- landmarks / POIs (e.g. "Connaught Place") resolve to a single Point
        and will raise a TypeError. Use center_point instead for those.
      - center_point=(lat, lon): draws a circular network of radius `dist`
        meters around an exact coordinate. Always works regardless of how
        Nominatim classifies the location.
    """
    if center_point is not None:
        G = ox.graph_from_point(center_point, dist=dist, network_type="walk")
    else:
        G = ox.graph_from_place(place_name, network_type="walk")

    _, gdf_edges = ox.graph_to_gdfs(G)

    gdf_edges=gdf_edges.reset_index()


    # OSMnx emits reciprocal edges for walk networks (u->v and v->u are the
    # same physical street). Keep one row per undirected pair, or lights get
    # split arbitrarily between the twins at snap time.
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
    engine = create_engine(db_url)
    edges.to_postgis('road_segments', engine, if_exists='append', index=False)

# this file takes in the raw osmx data.
# takes place name (or a center point + radius) and the db as parameters
# and writes the data into postgres