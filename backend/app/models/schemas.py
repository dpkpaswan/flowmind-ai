"""FlowMind AI — Pydantic Schemas.

Request and response models for all API endpoints.  These models
provide input validation, serialisation, and auto-generated OpenAPI
documentation via FastAPI's integration with Pydantic.

The models are **not** enforced on responses yet (the services return
plain dicts for flexibility), but they serve as the canonical schema
reference and can be wired in as ``response_model`` when ready.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

__all__ = [
    # Enums
    "FacilityType",
    "AlertSeverity",
    "ZoneStatus",
    # Zone / Crowd
    "Coordinates",
    "ZoneData",
    "CrowdPrediction",
    "HeatmapPoint",
    "CrowdOverview",
    # Wait Times
    "WaitTimeData",
    "BestAlternative",
    # Alerts
    "Alert",
    # Chat
    "ChatRequest",
    "ChatResponse",
    # Dashboard
    "StadiumOverview",
]


# ── Enums ────────────────────────────────────────────────────────────────────


class FacilityType(str, Enum):
    """Types of stadium facilities that fans can visit.

    Attributes:
        FOOD_STALL: Food and beverage stalls.
        RESTROOM: Restroom / washroom facilities.
        GATE: Entry/exit gates.
        MERCHANDISE: Merchandise shops.
    """

    FOOD_STALL = "food_stall"
    RESTROOM = "restroom"
    GATE = "gate"
    MERCHANDISE = "merchandise"


class AlertSeverity(str, Enum):
    """Alert severity levels, ordered from lowest to highest.

    Attributes:
        INFO: Informational — no immediate action needed.
        WARNING: Warning — action recommended within 10 min.
        CRITICAL: Critical — immediate action required.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ZoneStatus(str, Enum):
    """Zone crowd-density status labels.

    Thresholds (defined in ``config.Settings``):
        * LOW:      < 40 % density
        * MODERATE: 40–74 %
        * HIGH:     75–89 %
        * CRITICAL: 90 %+
    """

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# ── Zone / Crowd Models ─────────────────────────────────────────────────────


class Coordinates(BaseModel):
    """Geographic coordinates for a stadium zone centroid.

    Attributes:
        lat: Latitude in decimal degrees.
        lng: Longitude in decimal degrees.
    """

    lat: float
    lng: float


class ZoneData(BaseModel):
    """Real-time data for a single stadium zone.

    Attributes:
        zone_id: Unique zone identifier (e.g. ``"north_stand"``).
        name: Human-readable zone name.
        current_density: Live density (0.0–1.0).
        predicted_density: 15-min density prediction (0.0–1.0).
        status: Crowd status label derived from density.
        capacity: Maximum zone capacity.
        current_count: Current head-count.
        coordinates: Zone centroid lat/lng.
        prediction_minutes: Prediction horizon in minutes.
    """

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
    """Congestion prediction for a single zone.

    Attributes:
        zone_id: Zone identifier.
        name: Zone display name.
        current_density: Current density value.
        predictions: List of ``{minutes_ahead, predicted_density}`` dicts.
    """

    zone_id: str
    name: str
    current_density: float
    predictions: List[dict] = Field(
        ..., description="List of {minutes_ahead, predicted_density} objects"
    )


class HeatmapPoint(BaseModel):
    """A single data point for the Google Maps heatmap overlay.

    Attributes:
        lat: Latitude in decimal degrees.
        lng: Longitude in decimal degrees.
        weight: Density intensity (0.0–1.0).
    """

    lat: float
    lng: float
    weight: float = Field(..., ge=0, le=1, description="Density intensity for heatmap")


class CrowdOverview(BaseModel):
    """Stadium-wide crowd overview returned by ``/api/crowd/current``.

    Attributes:
        stadium_name: Display name of the stadium.
        total_capacity: Maximum capacity.
        current_attendance: Current head-count.
        overall_density: Aggregate density (0.0–1.0).
        zones: Per-zone data list.
        timestamp: ISO 8601 UTC timestamp.
    """

    stadium_name: str
    total_capacity: int
    current_attendance: int
    overall_density: float
    zones: List[ZoneData]
    timestamp: str


# ── Wait Time Models ─────────────────────────────────────────────────────────


class WaitTimeData(BaseModel):
    """Real-time wait data for a single facility.

    Attributes:
        facility_id: Unique facility identifier.
        name: Human-readable facility name.
        facility_type: Category (e.g. ``food_stall``).
        zone_id: Parent zone identifier.
        current_wait_minutes: Live wait time in minutes.
        predicted_wait_minutes: 15-min predicted wait.
        queue_length: Number of people currently in the queue.
        is_open: Whether the facility is currently open.
    """

    facility_id: str
    name: str
    facility_type: FacilityType
    zone_id: str
    current_wait_minutes: float
    predicted_wait_minutes: float
    queue_length: int
    is_open: bool = True


class BestAlternative(BaseModel):
    """Best-alternative recommendation response.

    Attributes:
        recommended: The top-recommended facility.
        alternatives: Other options sorted by wait time.
        reason: Human-readable recommendation rationale.
    """

    recommended: WaitTimeData
    alternatives: List[WaitTimeData]
    reason: str


# ── Alert Models ─────────────────────────────────────────────────────────────


class Alert(BaseModel):
    """A single actionable alert.

    Attributes:
        alert_id: Unique 8-char UUID prefix.
        severity: Alert severity level.
        title: Short headline (may contain emoji).
        message: Detailed message with data context.
        zone_id: Affected zone (optional for global alerts).
        zone_name: Human-readable zone name.
        action: Recommended user action.
        timestamp: ISO 8601 UTC timestamp.
        expires_in_minutes: Minutes until the alert is stale.
    """

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
    """Request body for the AI chat endpoint.

    Attributes:
        message: The fan's question (1–500 characters).
        user_location: Optional current zone for location-aware answers.
        language: ISO 639-1 response language code.
    """

    message: str = Field(..., min_length=1, max_length=500)
    user_location: Optional[str] = Field(
        None, description="User's current zone for context"
    )
    language: str = Field(
        default="en", description="Response language code (en, hi, es, fr, etc.)"
    )


class ChatResponse(BaseModel):
    """Response body from the AI chat endpoint.

    Attributes:
        response: The AI-generated answer text.
        recommended_action: Extracted actionable sentence, if any.
        confidence: Confidence score (0.0–1.0).
        related_zones: Zone names referenced in the response.
        timestamp: ISO 8601 UTC timestamp.
    """

    response: str
    recommended_action: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    related_zones: List[str] = []
    timestamp: str


# ── Dashboard Models ─────────────────────────────────────────────────────────


class StadiumOverview(BaseModel):
    """Aggregated dashboard overview.

    Attributes:
        stadium_name: Display name of the stadium.
        total_capacity: Maximum capacity.
        current_attendance: Current head-count.
        overall_density: Aggregate density (0.0–1.0).
        busiest_zone: Name of the most crowded zone.
        quietest_zone: Name of the least crowded zone.
        active_alerts: Number of active alerts.
        avg_wait_food: Average food-stall wait time.
        avg_wait_restroom: Average restroom wait time.
        avg_wait_gate: Average gate wait time.
        timestamp: ISO 8601 UTC timestamp.
    """

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
