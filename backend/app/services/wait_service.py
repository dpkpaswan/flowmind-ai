"""
FlowMind AI — Wait Time Prediction Service
Estimates and predicts wait times for food stalls, restrooms, and gates.
"""

from typing import Dict, List, Optional

from app.data.firebase_client import db
from app.data.mock_generator import generate_snapshot, FACILITIES
from app.utils.helpers import clamp, now_iso


def get_all_wait_times() -> List[Dict]:
    """Return current wait times for all facilities with predictions."""
    snapshot = generate_snapshot()
    facilities = snapshot["facilities"]
    zones = snapshot["zones"]

    result = []
    for fid, fdata in facilities.items():
        zone_density = zones.get(fdata["zone_id"], {}).get("current_density", 0.5)
        predicted = _predict_wait(fdata["current_wait_minutes"], zone_density)

        result.append({
            **fdata,
            "predicted_wait_minutes": round(predicted, 1),
        })

    # Sort by current wait (longest first)
    result.sort(key=lambda x: x["current_wait_minutes"], reverse=True)
    return result


def predict_facility_wait(facility_id: str, minutes_ahead: int = 15) -> Optional[Dict]:
    """Predict wait time for a specific facility N minutes into the future."""
    snapshot = generate_snapshot()
    fdata = snapshot["facilities"].get(facility_id)

    if not fdata:
        return None

    zones = snapshot["zones"]
    zone_density = zones.get(fdata["zone_id"], {}).get("current_density", 0.5)

    predictions = []
    for minutes in [5, 10, 15]:
        if minutes > minutes_ahead:
            break
        pred = _predict_wait(fdata["current_wait_minutes"], zone_density, minutes)
        predictions.append({
            "minutes_ahead": minutes,
            "predicted_wait_minutes": round(pred, 1),
        })

    return {
        **fdata,
        "predictions": predictions,
    }


def get_best_alternative(facility_type: str) -> Dict:
    """
    Find the best (least-crowded) alternative for a given facility type.
    Returns the recommended facility and a ranked list of alternatives.
    """
    snapshot = generate_snapshot()
    facilities = snapshot["facilities"]
    zones = snapshot["zones"]

    # Filter by type and open status
    matching = []
    for fid, fdata in facilities.items():
        if fdata["facility_type"] == facility_type and fdata.get("is_open", True):
            zone_density = zones.get(fdata["zone_id"], {}).get("current_density", 0.5)
            predicted = _predict_wait(fdata["current_wait_minutes"], zone_density)
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

    # Sort by current wait time (shortest first)
    matching.sort(key=lambda x: x["current_wait_minutes"])

    recommended = matching[0]
    alternatives = matching[1:]

    # Build reason
    if recommended["current_wait_minutes"] < 3:
        reason = f"{recommended['name']} has almost no wait right now — go now!"
    elif len(alternatives) > 0 and alternatives[0]["current_wait_minutes"] - recommended["current_wait_minutes"] > 3:
        reason = (
            f"{recommended['name']} is your best bet with a "
            f"{recommended['current_wait_minutes']:.0f} min wait. "
            f"The next closest option is {alternatives[0]['current_wait_minutes']:.0f} min longer."
        )
    else:
        reason = (
            f"{recommended['name']} currently has the shortest wait "
            f"at {recommended['current_wait_minutes']:.0f} minutes."
        )

    return {
        "recommended": recommended,
        "alternatives": alternatives,
        "reason": reason,
    }


def _predict_wait(current_wait: float, zone_density: float, minutes_ahead: int = 15) -> float:
    """
    Predict future wait time based on current wait and zone density trend.
    Higher density zones will see increasing waits; lower density zones will decrease.
    """
    # Density-driven trend
    if zone_density > 0.8:
        trend = 0.3 * (minutes_ahead / 5)   # Increasing wait
    elif zone_density > 0.5:
        trend = 0.1 * (minutes_ahead / 5)   # Slight increase
    else:
        trend = -0.2 * (minutes_ahead / 5)  # Decreasing wait

    import random
    noise = random.gauss(0, 0.5)
    predicted = current_wait + trend + noise
    return max(0.5, predicted)
