import pytest
import networkx as nx
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def test_client():
    """Returns a test client for hitting FastAPI endpoints directly."""
    return TestClient(app)

@pytest.fixture
def mock_graph():
    """
    Creates a simple 4-node grid graph to test routing logic:
    
    (0.0, 0.0) --- Edge 1 (Short, Dark) ---> (0.0, 1.0)
        |                                       |
     Edge 2 (Safe)                           Edge 3 (Safe)
        |                                       |
    (1.0, 0.0) --- Edge 4 (Safe) -------------> (1.0, 1.0)
    """
    G = nx.MultiDiGraph()
    
    # Path A: Direct but dark
    G.add_edge((0.0, 0.0), (1.0, 1.0), id=1, length_m=100.0, dark_fraction=0.9, longest_gap_m=90.0)
    
    # Path B: Longer but fully lit detour
    G.add_edge((0.0, 0.0), (0.0, 1.0), id=2, length_m=60.0, dark_fraction=0.0, longest_gap_m=0.0)
    G.add_edge((0.0, 1.0), (1.0, 1.0), id=3, length_m=60.0, dark_fraction=0.0, longest_gap_m=0.0)
    
    return G