"""FlowMind AI — Wait Time Prediction Service.

Estimates and predicts wait times for food stalls, restrooms, and gates.
The prediction model uses a density-driven trend: zones above 80 %
density see rising waits, while zones below 50 % see falling waits.

Performance notes:
    * All functions call ``generate_snapshot()`` which is O(1) on cache hit.
    * Sorting is O(F log F) where F = number of facilities (13).
    * ``get_best_alternative()`` filters by type first, reducing F to 4–5.
"""

import random
from typing import Any, Dict, List, Optional

from app.data.mock_generator import generate_snapshot
from app.exceptions import FacilityNotFoundError, InvalidFacilityTypeError
from app.utils.helpers import now_iso

__all__ = [
    "get_all_wait_times",
    "predict_facility_wait",
    "get_best_alternative",
]


def get_all_wait_times() -> List[Dict[str, Any]]:
    """Return current wait times for all facilities with predictions.

    Each facility record is enriched with a ``predicted_wait_minutes``
    field (15-min forecast).  Results are sorted longest-wait-first so
    the frontend can highlight the worst queues at the top.

    Returns:
        A list of facility dicts sorted by descending current wait time.

    Complexity:
        Time:  O(F log F) — iterate F facilities + sort.
        Space: O(F) for the result list.
    """
    snapshot: Dict[str, Any] = generate_snapshot()
    facilities: Dict[str, Dict] = snapshot["facilities"]
    zones: Dict[str, Dict] = snapshot["zones"]

    result: List[Dict[str, Any]] = []
    for _fid, fdata in facilities.items():
        # Look up the parent zone's density to feed the prediction model
        zone_density: float = zones.get(fdata["zone_id"], {}).get("current_density", 0.5)
        predicted: float = _predict_wait(fdata["current_wait_minutes"], zone_density)

        result.append({
            **fdata,
            "predicted_wait_minutes": round(predicted, 1),
        })

    # Sort by current wait (longest first) — fans care most about the worst queues
    result.sort(key=lambda x: x["current_wait_minutes"], reverse=True)
    return result


def predict_facility_wait(facility_id: str, minutes_ahead: int = 15) -> Dict[str, Any]:
    """Predict wait time for a specific facility N minutes into the future.

    Predictions are generated at 5-minute intervals up to
    ``minutes_ahead``.

    Args:
        facility_id: Unique facility identifier (e.g. ``"food_1"``).
        minutes_ahead: Maximum prediction horizon in minutes (default 15).

    Returns:
        Facility dict enriched with a ``predictions`` list.

    Raises:
        FacilityNotFoundError: If ``facility_id`` does not match any
            facility in the current snapshot.

    Complexity:
        Time:  O(1) for the dict lookup + O(1) per prediction step.
        Space: O(1) — at most 3 prediction entries.
    """
    snapshot: Dict[str, Any] = generate_snapshot()
    fdata: Optional[Dict] = snapshot["facilities"].get(facility_id)

    if not fdata:
        raise FacilityNotFoundError(facility_id)

    zones: Dict[str, Dict] = snapshot["zones"]
    zone_density: float = zones.get(fdata["zone_id"], {}).get("current_density", 0.5)

    predictions: List[Dict[str, Any]] = []
    for minutes in [5, 10, 15]:
        if minutes > minutes_ahead:
            break
        pred: float = _predict_wait(fdata["current_wait_minutes"], zone_density, minutes)
        predictions.append({
            "minutes_ahead": minutes,
            "predicted_wait_minutes": round(pred, 1),
        })

    return {
        **fdata,
        "predictions": predictions,
    }


def get_best_alternative(facility_type: str) -> Dict[str, Any]:
    """Find the best (least-crowded) open facility of a given type.

    Filters facilities by ``facility_type``, sorts by current wait time,
    and returns the top recommendation with a human-readable reason.

    Args:
        facility_type: One of ``"food_stall"``, ``"restroom"``,
            ``"gate"``, ``"merchandise"``.

    Returns:
        A dict with keys:
            - ``recommended`` (dict | None): Best facility, or None.
            - ``alternatives`` (list[dict]): Remaining options, ranked.
            - ``reason`` (str): Human-readable recommendation rationale.

    Raises:
        InvalidFacilityTypeError: If ``facility_type`` is not one of the
            accepted values.

    Complexity:
        Time:  O(F log F) — filter + sort matching facilities.
        Space: O(F') where F' = number of matching facilities (4–5).
    """
    if facility_type not in InvalidFacilityTypeError.VALID_TYPES:
        raise InvalidFacilityTypeError(facility_type)

    snapshot: Dict[str, Any] = generate_snapshot()
    facilities: Dict[str, Dict] = snapshot["facilities"]
    zones: Dict[str, Dict] = snapshot["zones"]

    # Filter to only open facilities of the requested type
    matching: List[Dict[str, Any]] = []
    for _fid, fdata in facilities.items():
        if fdata["facility_type"] == facility_type and fdata.get("is_open", True):
            zone_density: float = zones.get(fdata["zone_id"], {}).get("current_density", 0.5)
            predicted: float = _predict_wait(fdata["current_wait_minutes"], zone_density)
            matching.append({
                **fdata,
                "predicted_wait_minutes": round(predicted, 1),
            })

    if not matching:
        return {
            "recommended": None,
            "alternatives": [],
            "reason": f"No open {facility_type.replace('_', ' ')}s found.",
        }

    # Sort by current wait time — shortest first is the "best" pick
    matching.sort(key=lambda x: x["current_wait_minutes"])

    recommended: Dict[str, Any] = matching[0]
    alternatives: List[Dict[str, Any]] = matching[1:]

    # Build a context-aware recommendation reason
    reason: str
    if recommended["current_wait_minutes"] < 3:
        # Essentially no wait — strong recommendation
        reason = f"{recommended['name']} has almost no wait right now — go now!"
    elif alternatives and alternatives[0]["current_wait_minutes"] - recommended["current_wait_minutes"] > 3:
        # Clear winner — large gap to second-best option
        reason = (
            f"{recommended['name']} is your best bet with a "
            f"{recommended['current_wait_minutes']:.0f} min wait. "
            f"The next closest option is {alternatives[0]['current_wait_minutes']:.0f} min longer."
        )
    else:
        # Close call — mention the specific wait time
        reason = (
            f"{recommended['name']} currently has the shortest wait "
            f"at {recommended['current_wait_minutes']:.0f} minutes."
        )

    return {
        "recommended": recommended,
        "alternatives": alternatives,
        "reason": reason,
    }


# ── Private Helpers ─────────────────────────────────────────────────────────


def _predict_wait(current_wait: float, zone_density: float, minutes_ahead: int = 15) -> float:
    """Predict future wait time using a density-driven trend model.

    Logic:
        * Zones at >80 % density → waits are *increasing* (congestion builds).
        * Zones at 50–80 % → waits *slowly increase* (moderate traffic).
        * Zones at <50 % → waits *decrease* (crowd is thinning out).
    A Gaussian noise term (σ=0.5 min) adds realistic jitter.

    Args:
        current_wait: Current wait time in minutes.
        zone_density: Parent zone's density (0.0–1.0).
        minutes_ahead: Prediction horizon in minutes.

    Returns:
        Predicted wait time in minutes, floored at 0.5.

    Complexity:
        Time:  O(1) — arithmetic + one gauss() call.
        Space: O(1).
    """
    # Density-driven trend: higher density → longer future waits
    trend: float
    if zone_density > 0.8:
        trend = 0.3 * (minutes_ahead / 5)   # ~0.3 min added per 5-min step
    elif zone_density > 0.5:
        trend = 0.1 * (minutes_ahead / 5)   # ~0.1 min added per 5-min step
    else:
        trend = -0.2 * (minutes_ahead / 5)  # waits shrink in uncrowded zones

    noise: float = random.gauss(0, 0.5)
    predicted: float = current_wait + trend + noise
    return max(0.5, predicted)  # floor at 30 s to avoid showing "0 min wait"
