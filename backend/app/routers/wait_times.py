"""
FlowMind AI — Wait Times Router
Endpoints for facility wait times, predictions, and best alternatives.
"""

from fastapi import APIRouter, HTTPException

from app.services.wait_service import (
    get_all_wait_times,
    predict_facility_wait,
    get_best_alternative,
)

router = APIRouter(prefix="/api/wait-times", tags=["Wait Times"])


@router.get("")
async def all_wait_times():
    """
    Get current wait times for all facilities (food stalls, restrooms, gates).
    Includes predicted wait and queue lengths, sorted by longest wait first.
    """
    return {"facilities": get_all_wait_times()}


@router.get("/best/{facility_type}")
async def best_alternative(facility_type: str):
    """
    Find the best (least-crowded) open facility of a given type.
    Types: food_stall, restroom, gate, merchandise
    Returns the recommended facility, alternatives, and reasoning.
    """
    valid_types = ["food_stall", "restroom", "gate", "merchandise"]
    if facility_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid facility type. Must be one of: {', '.join(valid_types)}",
        )
    return get_best_alternative(facility_type)


@router.get("/{facility_id}/predict")
async def facility_prediction(facility_id: str, minutes_ahead: int = 15):
    """
    Predict wait time for a specific facility, up to N minutes ahead.
    Returns predictions at 5-minute intervals.
    """
    result = predict_facility_wait(facility_id, minutes_ahead)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found.")
    return result
