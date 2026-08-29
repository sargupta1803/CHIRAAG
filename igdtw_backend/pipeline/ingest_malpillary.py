import requests
import geopandas as gpd
from shapely.geometry import Point
from sqlalchemy import create_engine

def ingest_mapillary(bbox, access_token, db_url):
    url = f"https://graph.mapillary.com/map_features?fields=id,geometry&object_value=object--street-light&bbox={bbox}"
    headers = {"Authorization": f"OAuth {access_token}"}
    res = requests.get(url, headers=headers).json()
    
    features = []
    for item in res.get('data', []):
        coords = item['geometry']['coordinates']
        features.append({'mapillary_id': item['id'], 'geometry': Point(coords[0], coords[1])})
        
    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    engine = create_engine(db_url)
    gdf.to_postgis('streetlights', engine, if_exists='append', index=False)

#takes data from mapillary, and stores the streetlight data into postgis