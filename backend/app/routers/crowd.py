"""
FlowMind AI — Crowd Prediction Router
Endpoints for zone density, congestion predictions, and heatmap data.
"""

from fastapi import APIRouter

from app.services.crowd_service import (
    get_current_density,
    predict_congestion,
    get_heatmap_data,
)

router = APIRouter(prefix="/api/crowd", tags=["Crowd"])


@router.get("/current")
async def current_density():
    """
    Get current crowd density for all stadium zones.
    Returns zone-level density, status, attendance, and 15-min predictions.
    """
    return get_current_density()


@router.get("/predict")
async def crowd_prediction():
    """
    Get congestion predictions (5, 10, 15 minutes ahead) for all zones.
    Uses trend analysis on recent history for short-term forecasting.
    """
    return {"predictions": predict_congestion()}


@router.get("/heatmap")
async def heatmap_data():
    """
    Get heatmap-ready data points (lat, lng, weight) for map overlay.
    Multiple points per zone for smooth heatmap visualization.
    """
    return {"points": get_heatmap_data()}
