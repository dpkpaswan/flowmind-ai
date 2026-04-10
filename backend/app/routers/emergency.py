"""
FlowMind AI — Emergency Evacuation Router
Endpoints for triggering and managing emergency evacuation.
"""

from fastapi import APIRouter

from app.services.evacuation_service import (
    trigger_evacuation,
    cancel_evacuation,
    get_evacuation_status,
)

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])


@router.post("/evacuate")
async def evacuate():
    """
    Trigger emergency evacuation.
    Calculates optimal gate assignments for each zone based on proximity,
    current congestion, and gate throughput capacity.
    """
    return trigger_evacuation()


@router.post("/cancel")
async def cancel():
    """Cancel an active evacuation."""
    return cancel_evacuation()


@router.get("/status")
async def status():
    """Get current evacuation status and plan."""
    return get_evacuation_status()
