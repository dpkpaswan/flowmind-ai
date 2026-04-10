"""
FlowMind AI — Crowd Prediction Service
Handles crowd density analysis and short-term congestion prediction.
"""

from typing import Dict, List, Optional

from app.data.firebase_client import db
from app.data.mock_generator import generate_snapshot
from app.utils.helpers import clamp, density_to_status, now_iso


def get_current_density() -> Dict:
    """
    Return current zone density data for the entire stadium.
    Generates a fresh snapshot each call to reflect real-time changes.
    """
    snapshot = generate_snapshot()
    zones = snapshot["zones"]
    overview = snapshot["overview"]

    zone_list = []
    for zid, zdata in zones.items():
        # Attach a basic prediction (next 15 min)
        predicted = _simple_predict(zid, zdata["current_density"], minutes_ahead=15)
        zone_list.append({
            **zdata,
            "predicted_density": round(predicted, 3),
            "prediction_minutes": 15,
        })

    return {
        "stadium_name": overview["stadium_name"],
        "total_capacity": overview["total_capacity"],
        "current_attendance": overview["current_attendance"],
        "overall_density": overview["overall_density"],
        "zones": zone_list,
        "timestamp": overview["timestamp"],
    }


def predict_congestion() -> List[Dict]:
    """
    Return 10–15 minute congestion predictions for every zone.
    Each zone gets predictions at 5, 10, and 15 minute marks.
    """
    snapshot = generate_snapshot()
    zones = snapshot["zones"]
    predictions = []

    for zid, zdata in zones.items():
        current = zdata["current_density"]
        preds = []
        for minutes in [5, 10, 15]:
            pred = _simple_predict(zid, current, minutes)
            preds.append({
                "minutes_ahead": minutes,
                "predicted_density": round(pred, 3),
                "predicted_status": density_to_status(pred),
            })

        predictions.append({
            "zone_id": zid,
            "name": zdata["name"],
            "current_density": current,
            "current_status": zdata["status"],
            "predictions": preds,
        })

    return predictions


def get_heatmap_data() -> List[Dict]:
    """
    Return heatmap-ready data points with lat/lng/weight for map overlay.
    Generates multiple points per zone for smoother heatmap visualization.
    """
    snapshot = generate_snapshot()
    zones = snapshot["zones"]
    points = []

    for zid, zdata in zones.items():
        coord = zdata["coordinates"]
        density = zdata["current_density"]

        # Core point
        points.append({
            "lat": coord["lat"],
            "lng": coord["lng"],
            "weight": round(density, 3),
        })

        # Spread points around zone center for better heatmap coverage
        import random
        for _ in range(4):
            points.append({
                "lat": coord["lat"] + random.gauss(0, 0.0003),
                "lng": coord["lng"] + random.gauss(0, 0.0003),
                "weight": round(density * random.uniform(0.7, 1.0), 3),
            })

    return points


def _simple_predict(zone_id: str, current: float, minutes_ahead: int) -> float:
    """
    Simple trend-based prediction using recent history.
    Uses linear extrapolation on the last few data points,
    with mean-reversion to prevent runaway predictions.
    """
    history = db.get("/stadium/history") or []

    if len(history) < 3:
        # Not enough history — add small random drift
        import random
        drift = random.gauss(0.02, 0.03) * (minutes_ahead / 15)
        return clamp(current + drift)

    # Extract recent densities for this zone
    recent = []
    for h in history[-10:]:
        zone_hist = h.get("zones", {}).get(zone_id, {})
        if "density" in zone_hist:
            recent.append(zone_hist["density"])

    if len(recent) < 2:
        return clamp(current + 0.02)

    # Calculate trend (average rate of change)
    deltas = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    avg_delta = sum(deltas) / len(deltas)

    # Extrapolate with damping (mean reversion toward 0.5)
    steps = minutes_ahead / 2  # Each history step ≈ 30s, scale to minutes
    predicted = current + avg_delta * steps
    # Mean reversion: pull toward 0.55 to prevent extreme predictions
    predicted = predicted * 0.85 + 0.55 * 0.15

    return clamp(predicted, 0.05, 0.98)
