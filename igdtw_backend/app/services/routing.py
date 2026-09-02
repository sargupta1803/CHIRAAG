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
def _calculate_edge_weight(d: dict, lam: float) -> float:
    """
    d is a dict of {edge_key: attr_dict} for all parallel edges between u and v
    — this is the shape NetworkX passes to a custom weight function on a
    MultiDiGraph. We take the cheapest parallel edge, same as NetworkX's
    own default multigraph weight function does.
    """
    best = float("inf")
    for attrs in d.values():
        length = attrs.get("length_m", 1.0)
        dark_frac = attrs.get("dark_fraction", 0.0)
        unlit_length = dark_frac * length
        cost = length + (lam * unlit_length)
        best = min(best, cost)
    return best
def _get_path_metrics(G: nx.MultiDiGraph, path_nodes: list) -> dict:
    """
    Aggregates physical length and unlit metrics for a given path node sequence.
    """

    total_length = 0.0
    total_unlit = 0.0
    
    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i + 1]
        
        # Grab attributes of the connecting edge
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            # MultiDiGraph returns dict of parallel edges; grab key 0 for MVP
            data = edge_data[0]
            length = data.get("length_m", 0.0)
            dark_frac = data.get("dark_fraction", 0.0)
            
            total_length += length
            total_unlit += (dark_frac * length)
            
    return {
        "total_length_m": round(total_length, 2),
        "unlit_length_m": round(total_unlit, 2),
        "dark_fraction": round(total_unlit / total_length, 4) if total_length > 0 else 0.0
    }

def find_optimal_route(
    G: nx.MultiDiGraph,
    origin_coords: tuple[float, float],  # (lon, lat)
    dest_coords: tuple[float, float],    # (lon, lat)
    alpha: float = 1.20
) -> dict:
    """
    Executes lambda-sweep Dijkstra routing. Returns both the baseline (shortest)
    and safest feasible CHIRAAG route within the specified detour cap alpha.
    """
    
    start_node = _find_nearest_node(G, origin_coords)
    end_node = _find_nearest_node(G, dest_coords)
    
    if not start_node or not end_node:
        raise ValueError("Could not snap origin or destination to graph nodes.")

    # 1. Baseline Route (lambda = 0: pure physical distance)
    baseline_path = nx.dijkstra_path(
        G, start_node, end_node, 
        weight=lambda u, v, d: _calculate_edge_weight(d, lam=0.0)
    )
    baseline_metrics = _get_path_metrics(G, baseline_path)
    
    shortest_length = baseline_metrics["total_length_m"]
    max_allowed_length = alpha * shortest_length
    
    # 2. Lambda Sweep (sweep higher penalties to find safer routes)
    lambda_candidates = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
    best_path = baseline_path
    best_metrics = baseline_metrics
    
    for lam in lambda_candidates:
        candidate_path = nx.dijkstra_path(
            G, start_node, end_node,
            weight=lambda u, v, d: _calculate_edge_weight(d, lam=lam)
        )
        candidate_metrics = _get_path_metrics(G, candidate_path)
        
        # Check if route stays within detour multiplier cap alpha
        if candidate_metrics["total_length_m"] <= max_allowed_length:
            # Keep candidate if it reduces unlit exposure over current best
            if candidate_metrics["unlit_length_m"] < best_metrics["unlit_length_m"]:
                best_path = candidate_path
                best_metrics = candidate_metrics
        else:
            # Once detour cap is exceeded, higher lambdas will also exceed it
            break

    # 3. Construct Evidentiary Summary Stats
    unlit_avoided_m = baseline_metrics["unlit_length_m"] - best_metrics["unlit_length_m"]
    
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
            "unlit_meters_avoided": round(max(0.0, unlit_avoided_m), 2),
            "extra_distance_m": round(best_metrics["total_length_m"] - shortest_length, 2),
            "safety_gain_percent": round((unlit_avoided_m / baseline_metrics["unlit_length_m"] * 100), 1)
                                   if baseline_metrics["unlit_length_m"] > 0 else 0.0
        }
    }