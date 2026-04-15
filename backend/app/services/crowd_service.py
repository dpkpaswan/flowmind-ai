"""FlowMind AI — Crowd Prediction Service.

Handles crowd density analysis, zone-level status reporting, and
short-term congestion prediction using linear extrapolation on recent
history snapshots with mean-reversion damping.

Performance notes:
    * ``get_current_density()`` is the most-called endpoint (polled every
      15 s).  With the 10 s snapshot cache, ``generate_snapshot()`` is
      O(1) on cache hit.  The per-zone prediction loop is O(Z·H) worst
      case where Z = zones and H = history length (capped at 30).
    * ``get_heatmap_data()`` generates 5 points per zone (1 core +
      4 spread), totalling 40 points — well within Google Maps
      HeatmapLayer limits.
"""

import random
from typing import Any, Dict, List

from app.data.firebase_client import db
from app.data.mock_generator import generate_snapshot
from app.utils.helpers import clamp, density_to_status, now_iso

__all__ = [
    "get_current_density",
    "predict_congestion",
    "get_heatmap_data",
]


def get_current_density() -> Dict[str, Any]:
    """Return current zone density data for the entire stadium.

    Generates a fresh snapshot (or returns the cached version) and
    enriches each zone with a 15-minute density prediction.

    Returns:
        A dict containing:
            - ``stadium_name`` (str): Display name of the stadium.
            - ``total_capacity`` (int): Maximum stadium capacity.
            - ``current_attendance`` (int): Current head-count.
            - ``overall_density`` (float): Aggregate density 0.0–1.0.
            - ``zones`` (list[dict]): Per-zone data with predictions.
            - ``timestamp`` (str): ISO 8601 UTC timestamp.

    Raises:
        app.exceptions.SnapshotGenerationError: If snapshot generation
            fails (propagated from ``generate_snapshot``).

    Complexity:
        Time:  O(Z · H) — Z zones × H history depth for predictions.
        Space: O(Z) for the response list.
    """
    snapshot: Dict[str, Any] = generate_snapshot()
    zones: Dict[str, Dict] = snapshot["zones"]
    overview: Dict[str, Any] = snapshot["overview"]

    zone_list: List[Dict[str, Any]] = []
    for zid, zdata in zones.items():
        # Attach a 15-min density prediction for the frontend progress-bar markers
        predicted: float = _simple_predict(zid, zdata["current_density"], minutes_ahead=15)
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


def predict_congestion() -> List[Dict[str, Any]]:
    """Return 5 / 10 / 15-minute congestion predictions for every zone.

    Each zone receives three prediction entries at increasing time
    horizons, enabling the frontend to show trend arrows.

    Returns:
        A list of dicts, one per zone, each containing:
            - ``zone_id`` (str): Zone identifier.
            - ``name`` (str): Human-readable zone name.
            - ``current_density`` (float): Current density 0.0–1.0.
            - ``current_status`` (str): Status label (low/moderate/high/critical).
            - ``predictions`` (list[dict]): Predicted density at +5, +10, +15 min.

    Complexity:
        Time:  O(Z · H · 3) ≈ O(Z · H).
        Space: O(Z).
    """
    snapshot: Dict[str, Any] = generate_snapshot()
    zones: Dict[str, Dict] = snapshot["zones"]
    predictions: List[Dict[str, Any]] = []

    for zid, zdata in zones.items():
        current: float = zdata["current_density"]
        preds: List[Dict[str, Any]] = []
        for minutes in [5, 10, 15]:
            pred: float = _simple_predict(zid, current, minutes)
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


def get_heatmap_data() -> List[Dict[str, float]]:
    """Return heatmap-ready data points with lat/lng/weight for map overlay.

    For each zone, produces 1 core point at the zone centroid and 4
    Gaussian-spread satellite points for smoother Google Maps
    HeatmapLayer visualisation.

    Returns:
        A list of ``{"lat": float, "lng": float, "weight": float}`` dicts.
        Total count = ``len(ZONES) * 5`` (currently 40 points).

    Complexity:
        Time:  O(Z · 5) ≈ O(Z).
        Space: O(Z · 5) ≈ O(Z).
    """
    snapshot: Dict[str, Any] = generate_snapshot()
    zones: Dict[str, Dict] = snapshot["zones"]
    points: List[Dict[str, float]] = []

    for _zid, zdata in zones.items():
        coord: Dict[str, float] = zdata["coordinates"]
        density: float = zdata["current_density"]

        # Core point — exact zone centroid
        points.append({
            "lat": coord["lat"],
            "lng": coord["lng"],
            "weight": round(density, 3),
        })

        # Spread 4 satellite points around the centroid using Gaussian jitter
        # (σ ≈ 0.0003° ≈ 33 m) so the heatmap blob covers the entire zone area
        for _ in range(4):
            points.append({
                "lat": coord["lat"] + random.gauss(0, 0.0003),
                "lng": coord["lng"] + random.gauss(0, 0.0003),
                "weight": round(density * random.uniform(0.7, 1.0), 3),
            })

    return points


# ── Private Helpers ─────────────────────────────────────────────────────────


def _simple_predict(zone_id: str, current: float, minutes_ahead: int) -> float:
    """Predict future density using linear extrapolation + mean-reversion.

    The algorithm:
        1. Read the last 10 history snapshots from the mock DB.
        2. Compute per-step deltas (rate of change).
        3. Extrapolate forward by ``minutes_ahead`` steps.
        4. Apply mean-reversion (85 % signal + 15 % pull toward 0.55)
           to prevent runaway predictions at extreme densities.

    Args:
        zone_id: The zone to predict for (e.g. ``"north_stand"``).
        current: Current density value in [0, 1].
        minutes_ahead: How far ahead to predict, in minutes.

    Returns:
        Predicted density clamped to [0.05, 0.98].

    Complexity:
        Time:  O(H) where H = history length (capped at 30, reads last 10).
        Space: O(min(H, 10)) for the recent-densities slice.
    """
    history: list = db.get("/stadium/history") or []

    if len(history) < 3:
        # Not enough history for trend analysis — apply small random drift
        drift: float = random.gauss(0.02, 0.03) * (minutes_ahead / 15)
        return clamp(current + drift)

    # Extract the most recent density readings for this zone (up to 10)
    recent: List[float] = []
    for h in history[-10:]:
        zone_hist: Dict = h.get("zones", {}).get(zone_id, {})
        if "density" in zone_hist:
            recent.append(zone_hist["density"])

    if len(recent) < 2:
        # Still not enough data — return a conservative upward nudge
        return clamp(current + 0.02)

    # Calculate average rate of change across consecutive snapshots
    deltas: List[float] = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    avg_delta: float = sum(deltas) / len(deltas)

    # Extrapolate: each history step ≈ 30 s, so scale to requested minutes
    steps: float = minutes_ahead / 2
    predicted: float = current + avg_delta * steps

    # Mean-reversion toward 0.55 prevents predictions from saturating at
    # 0 % or 100 % — realistic crowds tend to oscillate around a mean
    predicted = predicted * 0.85 + 0.55 * 0.15

    return clamp(predicted, 0.05, 0.98)
