"""
FlowMind AI — Event Simulation Router
Endpoints to control the live event simulation (play/pause/speed).
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.services.simulation_service import (
    start_simulation,
    stop_simulation,
    set_simulation_speed,
    get_simulation_status,
)

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


class SimulationStartRequest(BaseModel):
    speed: float = Field(default=10.0, ge=1.0, le=60.0, description="Simulation speed multiplier (1x–60x)")


class SimulationSpeedRequest(BaseModel):
    speed: float = Field(..., ge=1.0, le=60.0)


@router.get("/status")
async def simulation_status():
    """Get current simulation state, phase, and progress."""
    return get_simulation_status()


@router.post("/start")
async def start_sim(request: SimulationStartRequest = SimulationStartRequest()):
    """
    Start the event simulation.
    Speed: 1x = real-time, 10x = demo mode (12 min), 30x = fast demo (4 min).
    """
    return start_simulation(speed=request.speed)


@router.post("/stop")
async def stop_sim():
    """Stop the simulation and reset to idle."""
    return stop_simulation()


@router.post("/speed")
async def change_speed(request: SimulationSpeedRequest):
    """Change simulation speed while running."""
    return set_simulation_speed(speed=request.speed)
