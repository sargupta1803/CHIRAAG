import math
import networkx as nx


def _dist(a, b) -> float:
    """
    Planar distance between two (lon, lat) tuples.

    Only used for comparing which end of a stored geometry is nearer to a
    given node, so degree-space is fine -- no metric accuracy needed.
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _find_nearest_node(
    G: nx.MultiDiGraph,
    target_coords: tuple[float, float]
) -> tuple[tuple[float, float] | None, float]:
    """
    Find the nearest graph node to a (lon, lat) pair.

    Returns (node, distance_in_metres). Longitude is scaled by cos(lat) so
    the comparison is a real distance and not a degree-space one -- at
    Delhi's latitude a degree of longitude is ~12% shorter than a degree
    of latitude, which skews east-west snapping otherwise.
    """
    target_lon, target_lat = target_coords

    lon_scale = 111320.0 * math.cos(math.radians(target_lat))
    lat_scale = 110574.0

    best_node = None
    min_dist = float("inf")

    for node in G.nodes():
        node_lon, node_lat = node

        dist = math.hypot(
            (node_lon - target_lon) * lon_scale,
            (node_lat - target_lat) * lat_scale,
        )

        if dist < min_dist:
            min_dist = dist
            best_node = node

    return best_node, min_dist


def _pick_edge(G: nx.MultiDiGraph, u, v) -> dict | None:
    """
    Choose one edge among parallel u->v edges.

    Single selection rule so that path metrics and the returned geometry
    always describe the same physical street.
    """
    edge_data = G.get_edge_data(u, v)

    if not edge_data:
        return None

    return min(
        edge_data.values(),
        key=lambda attrs: attrs.get("length_m", float("inf")),
    )


def _calculate_edge_weight(
    d: dict,
    lam: float,
    unknown_policy: str = "neutral"
) -> float:
    """
    Calculate routing cost for parallel edges.

    Known/predicted segments:
        cost = distance + lambda * unlit exposure

    Unknown segments:
        neutral    -> normal distance
        avoid      -> additional penalty
        show_gaps  -> normal distance
    """
    best = float("inf")

    for attrs in d.values():
        length = float(attrs.get("length_m", 1.0))
        dark_frac = attrs.get("dark_fraction")
        observation_state = attrs.get("observation_state", "unobserved")

        is_unknown = observation_state in {
            "unobserved",
            "unknown",
            "UNKNOWN"
        } or dark_frac is None

        if is_unknown:
            if unknown_policy == "avoid":
                # Unknown evidence gets a strong additive penalty.
                # This makes known roads preferable when a feasible
                # alternative exists, without calling unknown roads dark.
                cost = length + (lam * (length + 500.0))
            else:
                # neutral / show_gaps
                cost = length
        else:
            dark_frac = float(dark_frac or 0.0)
            unlit_length = dark_frac * length
            cost = length + (lam * unlit_length)

        best = min(best, cost)

    return best


def _path_segments(G: nx.MultiDiGraph, path_nodes: list) -> list[dict]:
    """
    Walk the path and return one entry per physical street, each with its
    own geometry and evidence. This is what lets the map colour streets
    individually and hang a click handler on them.
    """
    segments = []

    for u, v in zip(path_nodes, path_nodes[1:]):
        data = _pick_edge(G, u, v)

        if data is None:
            continue

        geom = data.get("geometry")

        if geom is None:
            coords = [tuple(u), tuple(v)]
        else:
            coords = [(x, y) for x, y in geom.coords]

            # Both directions share one stored geometry, so it may run v->u.
            if _dist(coords[0], u) > _dist(coords[-1], u):
                coords.reverse()

        segments.append({
            "road_id": data.get("id"),
            "length_m": round(float(data.get("length_m", 0.0)), 2),
            "dark_fraction": data.get("dark_fraction"),
            "observation_state": data.get("observation_state", "unobserved"),
            "coordinates": coords,
        })

    return segments


def _path_geometry(G: nx.MultiDiGraph, path_nodes: list, tol: float = 1e-9) -> list:
    """
    Flatten the per-segment geometries into one continuous coordinate list.
    """
    coords: list = []

    for segment in _path_segments(G, path_nodes):
        piece = segment["coordinates"]

        # Consecutive streets share a junction node -- don't emit it twice.
        if coords and _dist(coords[-1], piece[0]) < tol:
            piece = piece[1:]

        coords.extend(piece)

    return coords or [tuple(n) for n in path_nodes]


def _get_path_metrics(
    G: nx.MultiDiGraph,
    path_nodes: list,
    lam: float = 0.0,
    unknown_policy: str = "neutral"
) -> dict:
    """
    Aggregate physical length, known-unlit exposure, and unknown
    evidence length for a route.

    Unknown segments are NOT treated as dark.
    """

    total_length = 0.0
    total_unlit = 0.0
    unknown_length = 0.0

    for u, v in zip(path_nodes, path_nodes[1:]):
        data = _pick_edge(G, u, v)

        if data is None:
            continue

        length = float(data.get("length_m", 0.0))
        dark_frac = data.get("dark_fraction")
        observation_state = data.get("observation_state", "unobserved")

        total_length += length

        is_unknown = (
            observation_state in {
                "unobserved",
                "unknown",
                "UNKNOWN"
            }
            or dark_frac is None
        )

        if is_unknown:
            unknown_length += length
        else:
            total_unlit += float(dark_frac or 0.0) * length

    # Computed once after the loop -- a zero-edge path must not raise.
    coverage_ratio = (
        (total_length - unknown_length) / total_length
        if total_length > 0
        else 0.0
    )

    dark_fraction = (
        total_unlit / total_length
        if total_length > 0
        else 0.0
    )

    return {
        "total_length_m": round(total_length, 2),
        "unlit_length_m": round(total_unlit, 2),
        "unknown_length_m": round(unknown_length, 2),
        "dark_fraction": round(dark_fraction, 4),
        "coverage_ratio": round(coverage_ratio, 4),
    }


def find_optimal_route(
    G: nx.MultiDiGraph,
    origin_coords: tuple[float, float],
    dest_coords: tuple[float, float],
    alpha: float = 1.20,
    unknown_policy: str = "neutral",
    max_snap_m: float = 250.0
) -> dict:
    """
    Finds the shortest route first, then searches for a safer route
    that stays within the allowed detour cap.
    """

    start_node, start_dist = _find_nearest_node(G, origin_coords)
    end_node, end_dist = _find_nearest_node(G, dest_coords)

    if start_node is None or end_node is None:
        raise ValueError("Road network graph is empty.")

    # Snapping without a distance limit silently returns a route starting at
    # the edge of the mapped area when the request is outside it -- a wrong
    # answer presented as a correct one.
    if start_dist > max_snap_m:
        raise ValueError(
            f"Start point is {start_dist:.0f} m from the nearest mapped street. "
            f"CHIRAAG only covers a small area of Delhi right now."
        )

    if end_dist > max_snap_m:
        raise ValueError(
            f"Destination is {end_dist:.0f} m from the nearest mapped street. "
            f"CHIRAAG only covers a small area of Delhi right now."
        )

    # 1. True shortest-distance route
    try:
        baseline_path = nx.dijkstra_path(
            G,
            start_node,
            end_node,
            weight=lambda u, v, d: _calculate_edge_weight(
                d, lam=0.0, unknown_policy=unknown_policy
            )
        )
    except nx.NetworkXNoPath:
        raise ValueError(
            "No walking route exists between these points in the mapped network."
        )

    baseline_metrics = _get_path_metrics(
        G, baseline_path, lam=0.0, unknown_policy=unknown_policy
    )

    shortest_length = baseline_metrics["total_length_m"]
    max_allowed_length = alpha * shortest_length

    # 2. Search increasingly safety-focused routes
    lambda_candidates = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]

    best_path = baseline_path
    best_metrics = baseline_metrics

    for lam in lambda_candidates:
        candidate_path = nx.dijkstra_path(
            G,
            start_node,
            end_node,
            weight=lambda u, v, d: _calculate_edge_weight(
                d, lam=lam, unknown_policy=unknown_policy
            )
        )

        candidate_metrics = _get_path_metrics(
            G, candidate_path, lam=lam, unknown_policy=unknown_policy
        )

        # Reject routes exceeding the allowed detour.
        if candidate_metrics["total_length_m"] > max_allowed_length:
            continue

        # Compare safety exposure according to the unknown policy.
        candidate_exposure = candidate_metrics["unlit_length_m"]
        best_exposure = best_metrics["unlit_length_m"]

        if unknown_policy == "avoid":
            candidate_exposure += candidate_metrics["unknown_length_m"]
            best_exposure += best_metrics["unknown_length_m"]

        if candidate_exposure < best_exposure:
            best_path = candidate_path
            best_metrics = candidate_metrics

    unlit_avoided_m = (
        baseline_metrics["unlit_length_m"]
        - best_metrics["unlit_length_m"]
    )

    safety_gain_percent = (
        (unlit_avoided_m / baseline_metrics["unlit_length_m"]) * 100
        if baseline_metrics["unlit_length_m"] > 0
        else 0.0
    )

    return {
        "status": "success",
        "detour_multiplier_cap": alpha,

        "baseline_route": {
            "nodes": _path_geometry(G, baseline_path),
            "segments": _path_segments(G, baseline_path),
            "metrics": baseline_metrics
        },

        "chiraag_route": {
            "nodes": _path_geometry(G, best_path),
            "segments": _path_segments(G, best_path),
            "metrics": best_metrics
        },

        "evidence_summary": {
            "unlit_meters_avoided": round(max(0.0, unlit_avoided_m), 2),
            "extra_distance_m": round(
                best_metrics["total_length_m"] - shortest_length, 2
            ),
            "safety_gain_percent": round(safety_gain_percent, 1)
        }
    }