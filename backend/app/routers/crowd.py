"""FlowMind AI — Crowd Prediction Router.

Endpoints for zone density, congestion predictions, and heatmap data.
"""

from typing import Any, Dict

from fastapi import APIRouter

from app.services.crowd_service import (
    get_current_density,
    get_heatmap_data,
    predict_congestion,
)

__all__ = ["router"]

router = APIRouter(prefix="/api/crowd", tags=["Crowd"])


@router.get("/current")
async def current_density() -> Dict[str, Any]:
    """Get current crowd density for all stadium zones.

    Returns:
        Zone-level density, status, attendance, and 15-min predictions.
    """
    return get_current_density()


@router.get("/predict")
async def crowd_prediction() -> Dict[str, Any]:
    """Get congestion predictions (5, 10, 15 minutes ahead) for all zones.

    Returns:
        Per-zone predictions using trend analysis on recent history.
    """
    return {"predictions": predict_congestion()}


@router.get("/heatmap")
async def heatmap_data() -> Dict[str, Any]:
    """Get heatmap-ready data points (lat, lng, weight) for map overlay.

    Returns:
        Multiple points per zone for smooth heatmap visualisation.
    """
    return {"points": get_heatmap_data()}
