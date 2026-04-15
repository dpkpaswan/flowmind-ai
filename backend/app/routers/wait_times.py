"""FlowMind AI — Wait Times Router.

Endpoints for facility wait times, predictions, and best alternatives.
Uses custom exceptions for consistent error handling.
"""

from fastapi import APIRouter, HTTPException

from app.exceptions import FacilityNotFoundError, InvalidFacilityTypeError
from app.services.wait_service import (
    get_all_wait_times,
    get_best_alternative,
    predict_facility_wait,
)

__all__ = ["router"]

router = APIRouter(prefix="/api/wait-times", tags=["Wait Times"])


@router.get("")
async def all_wait_times():
    """Get current wait times for all facilities (food stalls, restrooms, gates).

    Returns:
        A JSON object with a ``facilities`` list sorted by longest wait first.
    """
    return {"facilities": get_all_wait_times()}


@router.get("/best/{facility_type}")
async def best_alternative(facility_type: str):
    """Find the best (least-crowded) open facility of a given type.

    Args:
        facility_type: One of ``food_stall``, ``restroom``, ``gate``,
            ``merchandise``.

    Returns:
        The recommended facility, ranked alternatives, and reasoning.

    Raises:
        HTTPException(400): If ``facility_type`` is invalid.
    """
    try:
        return get_best_alternative(facility_type)
    except InvalidFacilityTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{facility_id}/predict")
async def facility_prediction(facility_id: str, minutes_ahead: int = 15):
    """Predict wait time for a specific facility, up to N minutes ahead.

    Args:
        facility_id: Unique facility identifier (e.g. ``food_1``).
        minutes_ahead: Prediction horizon in minutes (default 15).

    Returns:
        Facility data enriched with prediction entries at 5-min intervals.

    Raises:
        HTTPException(404): If the facility ID is not found.
    """
    try:
        return predict_facility_wait(facility_id, minutes_ahead)
    except FacilityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
