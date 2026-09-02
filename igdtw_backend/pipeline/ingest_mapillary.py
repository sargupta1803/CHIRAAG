import requests
import geopandas as gpd
from shapely.geometry import Point
from sqlalchemy import create_engine, text

def ingest_mapillary(bbox, access_token, db_url):
    url = f"https://graph.mapillary.com/map_features?fields=id,geometry&object_value=object--street-light&bbox={bbox}"
    headers = {"Authorization": f"OAuth {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Mapillary API returned HTTP {response.status_code}: {response.text}")
        response.raise_for_status()

    res = response.json()

    if 'data' not in res:
        print(f"Mapillary response had no 'data' key -- full response: {res}")

    raw_data = res.get('data', [])
    print(f"Mapillary returned {len(raw_data)} street-light features for bbox={bbox}")

    features = []
    for item in raw_data:
        coords = item['geometry']['coordinates']
        features.append({'mapillary_id': item['id'], 'geometry': Point(coords[0], coords[1])})

    if not features:
        print("No streetlight features to insert -- skipping DB write.")
        return

    engine = create_engine(db_url)

    # mapillary_id is unique in the DB -- skip any we've already ingested so
    # re-running this (e.g. on an overlapping bbox) doesn't crash on
    # duplicate-key violations.
    with engine.connect() as conn:
        existing_ids = {
            row[0] for row in conn.execute(text("SELECT mapillary_id FROM streetlights"))
        }
    new_features = [f for f in features if str(f['mapillary_id']) not in existing_ids]
    skipped = len(features) - len(new_features)
    if skipped:
        print(f"Skipping {skipped} street lights already in the database.")

    if not new_features:
        print("Nothing new to insert -- all features already exist.")
        return

    gdf = gpd.GeoDataFrame(new_features, geometry='geometry', crs="EPSG:4326")
    gdf = gdf.rename_geometry('geom')
    gdf.to_postgis('streetlights', engine, if_exists='append', index=False)
    print(f"Inserted {len(new_features)} new street lights.")

#takes data from mapillary, and stores the streetlight data into postgis