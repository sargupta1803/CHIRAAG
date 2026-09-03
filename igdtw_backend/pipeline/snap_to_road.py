import geopandas as gpd

def snap_lights_to_roads(roads_gdf, lights_gdf):
    roads_projected = roads_gdf.to_crs(epsg=32643)
    lights_projected = lights_gdf.to_crs(epsg=32643)
    roads_indexed = roads_projected.set_index('id')

    
    joined = gpd.sjoin_nearest(lights_projected, roads_projected, max_distance=25, distance_col="dist")
    
    snapped_data = {}
    for idx, row in joined.iterrows():
        road_id = row['id_right']
        road_geom = roads_indexed.loc[road_id, 'geometry']
        point_geom = row['geometry']
        
        distance_along_road = road_geom.project(point_geom)
        
        if road_id not in snapped_data:
            snapped_data[road_id] = []
        snapped_data[road_id].append(distance_along_road)
        
    for r_id in snapped_data:
        snapped_data[r_id].sort()
        
    return snapped_data