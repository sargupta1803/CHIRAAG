import math
import os
import sys
import hashlib

import osmnx as ox
from geoalchemy2 import WKTElement
from shapely.geometry import LineString

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from app.db import SessionLocal, Base, engine
from app.models.road_segment import RoadSegment


# ---------------------------------------------------------------------------
# Demo locations
# ---------------------------------------------------------------------------

ROUTES = [
    {
        "name": "India Gate → Connaught Place",
        "origin": (28.612945, 77.229466),
        "destination": (28.631540, 77.216742),
    },
    {
        "name": "India Gate → Red Fort",
        "origin": (28.612947, 77.229470),
        "destination": (28.656252, 77.240981),
    },
    {
        "name": "Connaught Place → AIIMS",
        "origin": (28.631549, 77.216726),
        "destination": (28.567250, 77.210024),
    },
    {
        "name": "Saket → Connaught Place",
        "origin": (28.524451, 77.206573),
        "destination": (28.631540, 77.216742),
    },
    {
        "name": "Dwarka → IGI Airport",
        "origin": (28.592152, 77.046016),
        "destination": (28.556157, 77.100038),
    },
    {
        "name": "Anand Vihar → Connaught Place",
        "origin": (28.646953, 77.315215),
        "destination": (28.631552, 77.216682),
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deterministic_dark_fraction(osm_id, edge_key):
    """
    Generate stable demo lighting evidence from the OSM edge identity.

    This is intentionally deterministic so that every seed produces the
    same CHIRAAG demo behaviour.

    NOTE:
    This is DEMO evidence, not real lighting data.
    """

    raw = f"{osm_id}:{edge_key}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    value = int(digest[:8], 16) / 0xFFFFFFFF

    if value < 0.18:
        return 0.75

    if value < 0.55:
        return 0.45

    if value < 0.82:
        return 0.20

    return 0.08


def haversine_m(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * 6371000 * math.asin(math.sqrt(h))


def geometry_length_m(geometry):
    """
    Calculate approximate length of a LineString using its actual
    intermediate coordinates rather than endpoint-to-endpoint distance.
    """

    coords = list(geometry.coords)

    if len(coords) < 2:
        return 0.0

    total = 0.0

    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]

        total += haversine_m(
            (lat1, lon1),
            (lat2, lon2),
        )

    return total


def nearest_edge_geometry(G, point):
    """
    Return the nearest OSM edge to a lat/lon point.

    The returned edge retains its real OSM LineString geometry.
    """

    lat, lon = point

    edge = ox.distance.nearest_edges(
        G,
        X=lon,
        Y=lat,
    )

    u, v, key = edge

    attrs = G.edges[u, v, key]

    geometry = attrs.get("geometry")

    if geometry is None:
        geometry = LineString(
            [
                (G.nodes[u]["x"], G.nodes[u]["y"]),
                (G.nodes[v]["x"], G.nodes[v]["y"]),
            ]
        )

    return geometry


def route_network(origin, destination):
    """
    Download an OSM walking network large enough to contain both endpoints
    and the road network between them.
    """

    lat1, lon1 = origin
    lat2, lon2 = destination

    center = (
        (lat1 + lat2) / 2,
        (lon1 + lon2) / 2,
    )

    straight_distance = haversine_m(
        origin,
        destination,
    )

    # Give the network enough room to contain realistic alternate streets.
    # Minimum 2.5 km, otherwise roughly half the endpoint distance + 2 km.
    dist = max(
        2500,
        straight_distance / 2 + 2000,
    )

    print(
        f"    Downloading OSM walking network "
        f"(~{dist / 1000:.1f} km radius)..."
    )

    G = ox.graph.graph_from_point(
        center,
        dist=dist,
        dist_type="bbox",
        network_type="walk",
        simplify=True,
        retain_all=False,
    )

    return G


def edge_to_road_segment(
    osm_id,
    edge_key,
    geometry,
):
    """
    Convert one OSM edge into our RoadSegment database model.
    """

    length_m = geometry_length_m(geometry)

    if length_m <= 0:
        return None

    dark_fraction = deterministic_dark_fraction(
        osm_id,
        edge_key,
    )

    # Keep most demo evidence as predicted.
    # A small deterministic subset is marked audited.
    digest = hashlib.sha256(
        f"audit:{osm_id}:{edge_key}".encode("utf-8")
    ).hexdigest()

    audited = int(digest[:2], 16) < 45

    observation_state = (
        "audited"
        if audited
        else "predicted"
    )

    return RoadSegment(
        osm_id=int(osm_id),
        length_m=round(length_m, 2),
        dark_fraction=round(dark_fraction, 2),
        longest_gap_m=round(
            dark_fraction * length_m,
            2,
        ),
        calibrated_lighting_prob=round(
            1.0 - dark_fraction,
            2,
        ),
        observation_state=observation_state,
        geom=WKTElement(
            geometry.wkt,
            srid=4326,
        ),
    )


# ---------------------------------------------------------------------------
# Main seed operation
# ---------------------------------------------------------------------------

def seed_osm_networks():
    print("Creating database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print()
        print("Removing existing demo road segments...")

        db.query(RoadSegment).delete()
        db.commit()

        all_segments = []
        seen_edges = set()

        print()
        print("Downloading real OpenStreetMap road geometry...")
        print()

        for route in ROUTES:
            print(
                f"  → {route['name']}"
            )

            G = route_network(
                route["origin"],
                route["destination"],
            )

            print(
                f"    OSM graph: "
                f"{G.number_of_nodes()} nodes, "
                f"{G.number_of_edges()} directed edges"
            )

            # Convert every unique physical OSM edge into a DB segment.
            #
            # We intentionally retain the actual OSM geometry so that the
            # frontend can draw the road's real bends instead of connecting
            # endpoints with artificial straight lines.
            for u, v, key, attrs in G.edges(
                keys=True,
                data=True,
            ):
                osm_id = attrs.get("osmid")

                if isinstance(osm_id, list):
                    osm_id = osm_id[0]

                if osm_id is None:
                    osm_id = (
                        abs(hash((u, v, key)))
                        % 2_000_000_000
                    )

                geometry = attrs.get("geometry")

                if geometry is None:
                    geometry = LineString(
                        [
                            (
                                G.nodes[u]["x"],
                                G.nodes[u]["y"],
                            ),
                            (
                                G.nodes[v]["x"],
                                G.nodes[v]["y"],
                            ),
                        ]
                    )

                # OSMnx walk graphs can contain reciprocal directed edges
                # sharing the same physical geometry. Store one copy.
                geometry_key = (
                    int(osm_id),
                    geometry.wkb,
                )

                if geometry_key in seen_edges:
                    continue

                seen_edges.add(geometry_key)

                segment = edge_to_road_segment(
                    osm_id=osm_id,
                    edge_key=key,
                    geometry=geometry,
                )

                if segment is not None:
                    all_segments.append(segment)

            print(
                f"    ✓ Added real road geometry"
            )

        if not all_segments:
            raise RuntimeError(
                "No OSM road segments were downloaded."
            )

        db.add_all(all_segments)
        db.commit()

        print()
        print("==========================================")
        print("CHIRAAG OSM demo data seeded successfully!")
        print("==========================================")
        print(
            f"Road segments: {len(all_segments)}"
        )
        print()

        print("Demo corridors covered:")

        for route in ROUTES:
            print(
                f"  • {route['name']}"
            )

        print()
        print("Data characteristics:")
        print("  ✓ Real OpenStreetMap walking network")
        print("  ✓ Real road/intersection topology")
        print("  ✓ Real curved LINESTRING geometries")
        print("  ✓ Deterministic demo lighting evidence")
        print("  ✓ Audited + predicted evidence states")
        print()
        print(
            "NOTE: Lighting values are synthetic demo evidence."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_osm_networks()