"""
FlowMind AI — Pydantic Schemas
Request/response models for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────


class FacilityType(str, Enum):
    FOOD_STALL = "food_stall"
    RESTROOM = "restroom"
    GATE = "gate"
    MERCHANDISE = "merchandise"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ZoneStatus(str, Enum):
    LOW = "low"           # < 40% density
    MODERATE = "moderate"  # 40–74%
    HIGH = "high"          # 75–89%
    CRITICAL = "critical"  # 90%+


# ── Zone / Crowd Models ─────────────────────────────────────────────────────


class Coordinates(BaseModel):
    lat: float
    lng: float


class ZoneData(BaseModel):
    zone_id: str
    name: str
    current_density: float = Field(..., ge=0, le=1, description="0.0 to 1.0")
    predicted_density: float = Field(..., ge=0, le=1)
    status: ZoneStatus
    capacity: int
    current_count: int
    coordinates: Coordinates
    prediction_minutes: int = 15


class CrowdPrediction(BaseModel):
    zone_id: str
    name: str
    current_density: float
    predictions: List[dict] = Field(
        ..., description="List of {minutes_ahead, predicted_density} objects"
    )


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    weight: float = Field(..., ge=0, le=1, description="Density intensity for heatmap")


class CrowdOverview(BaseModel):
    stadium_name: str
    total_capacity: int
    current_attendance: int
    overall_density: float
    zones: List[ZoneData]
    timestamp: str


# ── Wait Time Models ─────────────────────────────────────────────────────────


class WaitTimeData(BaseModel):
    facility_id: str
    name: str
    facility_type: FacilityType
    zone_id: str
    current_wait_minutes: float
    predicted_wait_minutes: float
    queue_length: int
    is_open: bool = True


class BestAlternative(BaseModel):
    recommended: WaitTimeData
    alternatives: List[WaitTimeData]
    reason: str


# ── Alert Models ─────────────────────────────────────────────────────────────


class Alert(BaseModel):
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    action: str = Field(..., description="Recommended action for the user")
    timestamp: str
    expires_in_minutes: int = 10


# ── Chat Models ──────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    user_location: Optional[str] = Field(
        None, description="User's current zone for context"
    )
    language: str = Field(
        default="en", description="Response language code (en, hi, es, fr, etc.)"
    )


class ChatResponse(BaseModel):
    response: str
    recommended_action: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    related_zones: List[str] = []
    timestamp: str


# ── Dashboard Models ─────────────────────────────────────────────────────────


class StadiumOverview(BaseModel):
    stadium_name: str
    total_capacity: int
    current_attendance: int
    overall_density: float
    busiest_zone: str
    quietest_zone: str
    active_alerts: int
    avg_wait_food: float
    avg_wait_restroom: float
    avg_wait_gate: float
    timestamp: str
