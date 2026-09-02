from app.services.routing import find_optimal_route, _calculate_edge_weight

def test_edge_weight_calculation():
    """Verify exposure penalty increases cost correctly based on lambda."""
    edge_data = {"length_m": 100.0, "dark_fraction": 0.5}
    
    # Lambda = 0: Pure distance
    cost_lambda_0 = _calculate_edge_weight(None, None, None, edge_data, lam=0.0)
    assert cost_lambda_0 == 100.0
    
    # Lambda = 2.0: Distance + (2.0 * unlit_length) -> 100 + 2.0*(50) = 200
    cost_lambda_2 = _calculate_edge_weight(None, None, None, edge_data, lam=2.0)
    assert cost_lambda_2 == 200.0

def test_lambda_sweep_selects_safer_detour(mock_graph):
    """Verify that routing trades extra distance for lower unlit exposure."""
    origin = (0.0, 0.0)
    destination = (1.0, 1.0)
    
    # Alpha = 1.30 allows 30% detour (Direct=100m, Detour=120m -> 20% extra)
    result = find_optimal_route(
        G=mock_graph,
        origin_coords=origin,
        dest_coords=destination,
        alpha=1.30
    )
    
    assert result["status"] == "success"
    # Baseline shortest route should take the 100m dark edge
    assert result["baseline_route"]["metrics"]["total_length_m"] == 100.0
    assert result["baseline_route"]["metrics"]["dark_fraction"] == 0.9
    
    # CHIRAAG route should take the 120m lit path
    assert result["chiraag_route"]["metrics"]["total_length_m"] == 120.0
    assert result["chiraag_route"]["metrics"]["dark_fraction"] == 0.0
    assert result["evidence_summary"]["unlit_meters_avoided"] == 90.0