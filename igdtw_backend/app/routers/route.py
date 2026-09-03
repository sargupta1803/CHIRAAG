from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db  # Adjust import based on your DB session dependency helper
from app.schemas.route import RouteRequest, RouteResponse
from app.services.graph_builder import build_graph_from_db
from app.services.routing import find_optimal_route

router = APIRouter(
    prefix="/api/v1",
    tags=["Routing"]
)

@router.post(
    "/route", 
    response_model=RouteResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute dark-exposure minimized route"
)
def compute_route(
    payload: RouteRequest,
    db: Session = Depends(get_db)
):
    """
    Computes both the baseline shortest path and the safest CHIRAAG route 
    within the user-specified detour budget multiplier (alpha).
    """
    try:
        # 1. Build in-memory graph from PostGIS road segments
        G = build_graph_from_db(db)
        
        if G.number_of_nodes() == 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Road network graph is empty. Please run the ingestion pipeline first."
            )

        # 2. Extract origin & destination coordinates (lon, lat)
        origin_coords = (payload.origin.lon, payload.origin.lat)
        dest_coords = (payload.destination.lon, payload.destination.lat)

        # 3. Compute optimal route using lambda-sweep Dijkstra
        route_result = find_optimal_route(
            G=G,
            origin_coords=origin_coords,
            dest_coords=dest_coords,
            alpha=payload.alpha,
            unknown_policy=payload.unknown_policy
        )

        return route_result

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Routing failure: {str(e)}"
        )