"""FlowMind AI — Custom Exception Hierarchy.

All service-layer exceptions inherit from :class:`FlowMindError` so that
routers can catch a single base class and translate to the appropriate
HTTP status code.  Domain-specific subclasses carry structured context
(zone IDs, facility IDs, etc.) for richer error responses.

Typical usage in a router::

    from app.exceptions import FacilityNotFoundError

    try:
        result = predict_facility_wait(facility_id, minutes_ahead)
    except FacilityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
"""

from typing import Any, Dict, Optional

__all__ = [
    "FlowMindError",
    "SnapshotGenerationError",
    "FacilityNotFoundError",
    "InvalidFacilityTypeError",
    "SimulationStateError",
    "EvacuationError",
    "AIServiceError",
    "BigQueryError",
    "FirebaseError",
]


class FlowMindError(Exception):
    """Base exception for all FlowMind AI service errors.

    Attributes:
        message: Human-readable error description.
        details: Optional dict of structured context for logging/debugging.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialise with a message and optional structured details.

        Args:
            message: Human-readable error description.
            details: Optional key-value pairs for structured logging.
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ── Data Layer Exceptions ───────────────────────────────────────────────────


class SnapshotGenerationError(FlowMindError):
    """Raised when the stadium data snapshot cannot be generated.

    This is a critical error — most endpoints depend on snapshot data.
    """
    pass


class FirebaseError(FlowMindError):
    """Raised when a Firebase RTDB operation fails irrecoverably.

    Note: most Firebase failures are handled via silent fallback to the
    in-memory mock.  This exception is only raised when the caller
    explicitly needs to know about the failure.
    """
    pass


class BigQueryError(FlowMindError):
    """Raised when a BigQuery operation fails irrecoverably.

    Note: BigQuery logging is best-effort.  This exception is only
    raised by ``query_crowd_history()`` when the caller needs results
    and they cannot be obtained.
    """
    pass


# ── Service Layer Exceptions ────────────────────────────────────────────────


class FacilityNotFoundError(FlowMindError):
    """Raised when a requested facility ID does not exist.

    Attributes:
        facility_id: The ID that was not found.
    """

    def __init__(self, facility_id: str) -> None:
        """Initialise with the missing facility ID.

        Args:
            facility_id: The facility identifier that was not found.
        """
        self.facility_id = facility_id
        super().__init__(
            f"Facility '{facility_id}' not found.",
            details={"facility_id": facility_id},
        )


class InvalidFacilityTypeError(FlowMindError):
    """Raised when a facility type string is not one of the valid types.

    Attributes:
        facility_type: The invalid type that was provided.
        valid_types: List of accepted type strings.
    """

    VALID_TYPES = ("food_stall", "restroom", "gate", "merchandise")

    def __init__(self, facility_type: str) -> None:
        """Initialise with the invalid type.

        Args:
            facility_type: The invalid type string that was provided.
        """
        self.facility_type = facility_type
        self.valid_types = list(self.VALID_TYPES)
        super().__init__(
            f"Invalid facility type '{facility_type}'. "
            f"Must be one of: {', '.join(self.VALID_TYPES)}",
            details={"facility_type": facility_type, "valid_types": self.valid_types},
        )


class SimulationStateError(FlowMindError):
    """Raised when a simulation operation is invalid for the current state.

    Example: trying to change speed when the simulation is not running.
    """
    pass


class EvacuationError(FlowMindError):
    """Raised when an evacuation operation cannot be completed.

    Example: triggering evacuation when snapshot data is unavailable.
    """
    pass


class AIServiceError(FlowMindError):
    """Raised when the Gemini / Vertex AI service encounters a fatal error.

    Non-fatal errors (e.g. API timeout) are handled via the rule-based
    fallback and do **not** raise this exception.
    """
    pass
