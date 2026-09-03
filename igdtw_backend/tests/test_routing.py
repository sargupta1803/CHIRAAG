import networkx as nx
import pytest

from app.services.routing import (
    find_optimal_route,
    _calculate_edge_weight,
    _get_path_metrics,
    _path_geometry,
)


def _parallel(**attrs):
    """
    Wrap one edge's attributes the way NetworkX hands them to a weight
    function: a dict keyed by parallel-edge index.
    """
    return {0: attrs}


# --------------------------------------------------------------------------
# Edge cost
# --------------------------------------------------------------------------

def test_edge_weight_scales_with_lambda():
    """cost = length + lambda * (dark_fraction * length)"""
    edge = _parallel(
        length_m=100.0,
        dark_fraction=0.5,
        observation_state="predicted",
    )

    assert _calculate_edge_weight(edge, lam=0.0) == 100.0
    assert _calculate_edge_weight(edge, lam=2.0) == 200.0
    assert _calculate_edge_weight(edge, lam=10.0) == 600.0


def test_edge_weight_picks_cheapest_parallel_edge():
    """With parallel edges between the same nodes, the cheapest one wins."""
    edges = {
        0: dict(length_m=100.0, dark_fraction=0.9,
                observation_state="predicted"),
        1: dict(length_m=110.0, dark_fraction=0.0,
                observation_state="predicted"),
    }

    # lam=0 -> pure distance, the 100 m road wins.
    assert _calculate_edge_weight(edges, lam=0.0) == 100.0

    # lam=2 -> 100 + 2*90 = 280 vs 110 + 0 = 110, the lit road wins.
    assert _calculate_edge_weight(edges, lam=2.0) == 110.0


def test_unknown_segment_is_not_priced_as_dark():
    """An unobserved road costs plain distance under the neutral policy."""
    edge = _parallel(
        length_m=100.0,
        dark_fraction=None,
        observation_state="unobserved",
    )

    assert _calculate_edge_weight(edge, lam=10.0, unknown_policy="neutral") == 100.0


def test_avoid_policy_penalises_unknown_segments():
    """Under 'avoid', unknown roads take an additive penalty."""
    edge = _parallel(
        length_m=100.0,
        dark_fraction=None,
        observation_state="unobserved",
    )

    neutral = _calculate_edge_weight(edge, lam=2.0, unknown_policy="neutral")
    avoid = _calculate_edge_weight(edge, lam=2.0, unknown_policy="avoid")

    assert avoid > neutral
    # 100 + 2 * (100 + 500)
    assert avoid == 1300.0


# --------------------------------------------------------------------------
# Path metrics
# --------------------------------------------------------------------------

def test_metrics_on_empty_path_do_not_raise():
    """
    Regression: coverage_ratio used to be assigned inside the edge loop,
    so a path with no edges raised UnboundLocalError.
    """
    G = nx.MultiDiGraph()
    G.add_node((0.0, 0.0))

    metrics = _get_path_metrics(G, [(0.0, 0.0)])

    assert metrics["total_length_m"] == 0.0
    assert metrics["coverage_ratio"] == 0.0
    assert metrics["dark_fraction"] == 0.0


def test_unknown_length_is_separate_from_unlit(unknown_graph):
    """Unobserved road counts as unknown, never as unlit."""
    metrics = _get_path_metrics(
        unknown_graph, [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    )

    assert metrics["total_length_m"] == 120.0
    assert metrics["unlit_length_m"] == 0.0
    assert metrics["unknown_length_m"] == 120.0
    assert metrics["coverage_ratio"] == 0.0


# --------------------------------------------------------------------------
# Route selection
# --------------------------------------------------------------------------

def test_lambda_sweep_selects_safer_detour(mock_graph):
    """Routing trades extra distance for lower unlit exposure."""
    result = find_optimal_route(
        G=mock_graph,
        origin_coords=(0.0, 0.0),
        dest_coords=(1.0, 1.0),
        alpha=1.30,
    )

    assert result["status"] == "success"

    baseline = result["baseline_route"]["metrics"]
    assert baseline["total_length_m"] == 100.0
    assert baseline["dark_fraction"] == 0.9

    chiraag = result["chiraag_route"]["metrics"]
    assert chiraag["total_length_m"] == 120.0
    assert chiraag["dark_fraction"] == 0.0

    assert result["evidence_summary"]["unlit_meters_avoided"] == 90.0
    assert result["evidence_summary"]["extra_distance_m"] == 20.0
    assert result["evidence_summary"]["safety_gain_percent"] == 100.0


def test_detour_cap_rejects_the_safer_route(mock_graph):
    """
    With alpha=1.10 the 120 m detour exceeds the 110 m budget, so the
    dark baseline must be returned unchanged.
    """
    result = find_optimal_route(
        G=mock_graph,
        origin_coords=(0.0, 0.0),
        dest_coords=(1.0, 1.0),
        alpha=1.10,
    )

    assert result["chiraag_route"]["metrics"]["total_length_m"] == 100.0
    assert result["evidence_summary"]["unlit_meters_avoided"] == 0.0
    assert result["evidence_summary"]["extra_distance_m"] == 0.0


def test_graph_is_traversable_in_both_directions(mock_graph):
    """
    The DB holds one row per street; graph_builder adds both directions.
    Routing backwards must work as well as forwards.
    """
    result = find_optimal_route(
        G=mock_graph,
        origin_coords=(1.0, 1.0),
        dest_coords=(0.0, 0.0),
        alpha=1.30,
    )

    assert result["chiraag_route"]["metrics"]["total_length_m"] == 120.0


def test_unknown_policy_avoid_prefers_the_known_road(unknown_graph):
    """
    Under 'avoid', a known-dark road beats an unobserved detour, because
    unknown exposure is added to the comparison.
    """
    result = find_optimal_route(
        G=unknown_graph,
        origin_coords=(0.0, 0.0),
        dest_coords=(1.0, 1.0),
        alpha=1.30,
        unknown_policy="avoid",
    )

    assert result["chiraag_route"]["metrics"]["total_length_m"] == 100.0


# --------------------------------------------------------------------------
# Returned geometry
# --------------------------------------------------------------------------

def test_path_geometry_includes_interior_vertices(curved_graph):
    """
    Returned coordinates follow the street, not straight chords between
    intersections.
    """
    A = (77.2120, 28.6120)
    B = (77.2120, 28.6135)
    C = (77.2125, 28.6150)

    coords = _path_geometry(curved_graph, [A, B, C])

    assert len(coords) > 3
    assert tuple(coords[0]) == A
    assert tuple(coords[-1]) == C

    # The interior vertex of the curved street is present, in order.
    assert (77.2128, 28.6142) in [tuple(c) for c in coords]


def test_path_geometry_orients_reversed_edges(curved_graph):
    """
    The middle street is stored C->B but traversed B->C. Its vertices must
    come back in traversal order, with no duplicated junction node.
    """
    A = (77.2120, 28.6120)
    B = (77.2120, 28.6135)
    C = (77.2125, 28.6150)

    coords = [tuple(c) for c in _path_geometry(curved_graph, [A, B, C])]

    assert coords.index(B) < coords.index((77.2128, 28.6142)) < coords.index(C)
    assert len(coords) == len(set(coords))


def test_path_geometry_falls_back_without_geometry(mock_graph):
    """Synthetic graphs carrying no geometry still return endpoints."""
    coords = _path_geometry(mock_graph, [(0.0, 0.0), (1.0, 1.0)])

    assert [tuple(c) for c in coords] == [(0.0, 0.0), (1.0, 1.0)]