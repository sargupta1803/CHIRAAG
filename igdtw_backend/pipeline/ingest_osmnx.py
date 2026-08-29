import osmnx as ox
from sqlalchemy import create_engine
import geopandas as gpd

def ingest_osm(place_name="Piedmont, California, USA", db_url="postgresql://user:pass@localhost:5432/chiraag"):
    G=ox.graph_from_place(place_name, network_type="walk")
    _, gdf_edges = ox.graph_to_gdfs(G)

    edges=gdf_edges[['geometry','length']].reset_index()
    edges= edges.rename(columns={'length':'length_m','osmid':'osm_id'})

    engine=create_engine(db_url)
    edges.to_postgis('road_segments',engine, if_exists='append', index=False)

# this file takes in the raw osmx data.
# takes place name and the db as parameters and writes the data into postgres