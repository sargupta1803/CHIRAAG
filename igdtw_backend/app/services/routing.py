import math
import networkx as nx

def _find_nearest_node(G: nx.MultiDiGraph, target_coords: tuple[float, float]) -> tuple[float, float]:
    """
    Simple distance-based lookup to find the nearest graph node (lon, lat)
    for a given input coordinate pair (target_lon, target_lat).
    """
    target_lon, target_lat = target_coords
    best_node = None
    min_dist = float('inf')
    
    for node in G.nodes():
        node_lon, node_lat = node
        # Approximation for small-scale distance matching
        dist = math.hypot(node_lon - target_lon, node_lat - target_lat)
        if dist < min_dist:
            min_dist = dist
            best_node = node
            
    return best_node

# def _calculate_edge_weight(u, v, k, d, lam: float) -> float:
#     """
#     Dynamic cost function: C(e) = length_m + lambda * (dark_fraction * length_m)
#     """
#     length = d.get("length_m", 1.0)
#     dark_frac = d.get("dark_fraction", 0.0)
    
#     # Calculate unlit exposure distance penalty
#     unlit_length = dark_frac * length
    # return length + (lam * unlit_length)
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
        }

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

    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i + 1]

        edge_data = G.get_edge_data(u, v)

        if not edge_data:
            continue

        # Select the physically shortest parallel edge.
        data = min(
            edge_data.values(),
            key=lambda attrs: attrs.get(
                "length_m",
                float("inf")
            )
        )

        length = float(data.get("length_m", 0.0))
        dark_frac = data.get("dark_fraction")
        observation_state = data.get(
            "observation_state",
            "unobserved"
        )

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
            dark_frac = float(dark_frac or 0.0)
            total_unlit += dark_frac * length

        coverage_ratio = (
        (total_length - unknown_length) / total_length
        if total_length > 0
        else 0.0
    )

    return {
        "total_length_m": round(total_length, 2),
        "unlit_length_m": round(total_unlit, 2),
        "unknown_length_m": round(unknown_length, 2),
        "dark_fraction": round(
            total_unlit / total_length,
            4
        ) if total_length > 0 else 0.0,
        "coverage_ratio": round(coverage_ratio, 4)
    }

def find_optimal_route(
    G: nx.MultiDiGraph,
    origin_coords: tuple[float, float],
    dest_coords: tuple[float, float],
    alpha: float = 1.20,
    unknown_policy: str = "neutral"
) -> dict:
    """
    Finds the shortest route first, then searches for a safer route
    that stays within the allowed detour cap.
    """

    start_node = _find_nearest_node(G, origin_coords)
    end_node = _find_nearest_node(G, dest_coords)

    if start_node is None or end_node is None:
        raise ValueError("Could not snap origin or destination to graph nodes.")

    # 1. True shortest-distance route
    baseline_path = nx.dijkstra_path(
        G,
        start_node,
        end_node,
        weight=lambda u, v, d: _calculate_edge_weight(d, lam=0.0, unknown_policy=unknown_policy)
    )

    baseline_metrics = _get_path_metrics(G,baseline_path,lam=0.0,unknown_policy=unknown_policy)

    shortest_length = baseline_metrics["total_length_m"]

    known_length = (
        baseline_metrics["total_length_m"]
        - baseline_metrics["unknown_length_m"]
    )

    coverage_ratio = (
        known_length / baseline_metrics["total_length_m"]
        if baseline_metrics["total_length_m"] > 0
        else 0.0
    )

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
            weight=lambda u, v, d: _calculate_edge_weight(d, lam=lam, unknown_policy=unknown_policy)
        )

        candidate_metrics = _get_path_metrics(G,candidate_path,lam=lam,unknown_policy=unknown_policy)

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
            "nodes": baseline_path,
            "metrics": baseline_metrics
        },

        "chiraag_route": {
            "nodes": best_path,
            "metrics": best_metrics
        },

        "evidence_summary": {
            "unlit_meters_avoided": round(
                max(0.0, unlit_avoided_m), 2
            ),
            "extra_distance_m": round(
                best_metrics["total_length_m"] - shortest_length, 2
            ),
            "safety_gain_percent": round(
                safety_gain_percent, 1
            )
        }
    }