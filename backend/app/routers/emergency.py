"""FlowMind AI — Emergency Evacuation Router.

Endpoints for triggering and managing emergency evacuation.
Uses custom exceptions for consistent error handling.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.exceptions import EvacuationError
from app.services.evacuation_service import (
    cancel_evacuation,
    get_evacuation_status,
    trigger_evacuation,
)

__all__ = ["router"]

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])


@router.post("/evacuate")
async def evacuate() -> Dict[str, Any]:
    """Trigger emergency evacuation.

    Calculates optimal gate assignments for each zone based on proximity,
    current congestion, and gate throughput capacity.

    Returns:
        The full evacuation plan with zone assignments, gate summary,
        and general instructions.

    Raises:
        HTTPException(500): If the evacuation plan cannot be generated.
    """
    try:
        return trigger_evacuation()
    except EvacuationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/cancel")
async def cancel() -> Dict[str, Any]:
    """Cancel an active evacuation.

    Returns:
        A confirmation dict with ``active=False``.
    """
    return cancel_evacuation()


@router.get("/status")
async def status() -> Dict[str, Any]:
    """Get current evacuation status and plan.

    Returns:
        The active evacuation plan, or a dict indicating no active
        evacuation.
    """
    return get_evacuation_status()
