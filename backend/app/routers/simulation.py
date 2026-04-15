"""FlowMind AI — Event Simulation Router.

Endpoints to control the live event simulation (play/pause/speed).
Uses custom exceptions for consistent error handling.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.exceptions import SimulationStateError
from app.services.simulation_service import (
    get_simulation_status,
    set_simulation_speed,
    start_simulation,
    stop_simulation,
)

__all__ = ["router"]

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


class SimulationStartRequest(BaseModel):
    """Request body for starting a simulation.

    Attributes:
        speed: Simulation speed multiplier (1x–60x).
    """

    speed: float = Field(
        default=10.0, ge=1.0, le=60.0,
        description="Simulation speed multiplier (1x–60x)",
    )


class SimulationSpeedRequest(BaseModel):
    """Request body for changing simulation speed.

    Attributes:
        speed: New speed multiplier (1x–60x).
    """

    speed: float = Field(..., ge=1.0, le=60.0)


@router.get("/status")
async def simulation_status() -> Dict[str, Any]:
    """Get current simulation state, phase, and progress.

    Returns:
        Simulation state including phase, event minute, progress
        percentage, and the full event timeline.
    """
    return get_simulation_status()


@router.post("/start")
async def start_sim(
    request: SimulationStartRequest = SimulationStartRequest(),
) -> Dict[str, Any]:
    """Start the event simulation.

    Speed examples:
        * ``1`` = real-time (120 min)
        * ``10`` = demo mode (~12 min)
        * ``30`` = fast demo (~4 min)

    Returns:
        The current simulation status dict.
    """
    return start_simulation(speed=request.speed)


@router.post("/stop")
async def stop_sim() -> Dict[str, Any]:
    """Stop the simulation and reset to idle.

    Returns:
        The reset simulation status dict.
    """
    return stop_simulation()


@router.post("/speed")
async def change_speed(request: SimulationSpeedRequest) -> Dict[str, Any]:
    """Change simulation speed while running.

    Args:
        request: A ``SimulationSpeedRequest`` with the new speed.

    Returns:
        The updated simulation status dict.

    Raises:
        HTTPException(409): If the simulation is not currently running.
    """
    try:
        return set_simulation_speed(speed=request.speed)
    except SimulationStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
