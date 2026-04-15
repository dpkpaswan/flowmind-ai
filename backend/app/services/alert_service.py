"""FlowMind AI — Smart Alert Service.

Generates actionable alerts based on crowd density thresholds, wait time
thresholds, and crowd-surge trend detection.  Alerts are sorted by
severity (critical → warning → info) and persisted in the mock DB for
the ``/alerts/history`` endpoint.

Performance notes:
    * ``generate_alerts()`` is O(Z + F + H) where Z = zones, F = facilities,
      H = history length.  With snapshot caching the ``generate_snapshot()``
      call is O(1) on cache hit.
    * Alerts are not persisted long-term; the mock DB stores only the
      latest generated set.
"""

import uuid
from typing import Any, Dict, List

from app.config import settings
from app.data.firebase_client import db
from app.data.mock_generator import generate_snapshot
from app.utils.helpers import density_to_status, now_iso

__all__ = [
    "generate_alerts",
    "get_alert_history",
]

# Severity sort order — lower value = higher priority
_SEVERITY_ORDER: Dict[str, int] = {"critical": 0, "warning": 1, "info": 2}


def generate_alerts() -> List[Dict[str, Any]]:
    """Scan current stadium data and generate actionable alerts.

    Three alert sources are evaluated in sequence:
        1. **Zone density** — fires when a zone exceeds the configurable
           warning (75 %) or critical (90 %) thresholds.
        2. **Crowd surge** — fires when a zone's density has been rising
           >3 pp per snapshot *and* is already above 60 %.
        3. **Wait times** — fires when a facility's wait exceeds the
           configurable warning (10 min) or critical (20 min) thresholds.

    Returns:
        A list of alert dicts sorted by severity (critical first).

    Complexity:
        Time:  O(Z + F + H + A log A).
        Space: O(A) where A = number of generated alerts.
    """
    snapshot: Dict[str, Any] = generate_snapshot()
    zones: Dict[str, Dict] = snapshot["zones"]
    facilities: Dict[str, Dict] = snapshot["facilities"]
    alerts: List[Dict[str, Any]] = []

    # ── 1. Zone-based density alerts ─────────────────────────────────────
    # Compare each zone's density against the configurable thresholds.
    # Critical zones get a stronger "avoid" recommendation; warning zones
    # get a softer "consider leaving" nudge.
    for zid, zdata in zones.items():
        density: float = zdata["current_density"]

        if density >= settings.DENSITY_CRITICAL_THRESHOLD:
            alerts.append(_build_alert(
                severity="critical",
                title=f"🚨 {zdata['name']} is extremely crowded",
                message=(
                    f"{zdata['name']} has reached {density * 100:.0f}% capacity "
                    f"({zdata['current_count']:,} people). Avoid this area."
                ),
                zone_id=zid,
                zone_name=zdata["name"],
                action=f"Avoid {zdata['name']}. Use alternative routes or wait 10–15 minutes.",
                expires=5,
            ))
        elif density >= settings.DENSITY_WARNING_THRESHOLD:
            alerts.append(_build_alert(
                severity="warning",
                title=f"⚠️ {zdata['name']} is getting crowded",
                message=(
                    f"{zdata['name']} is at {density * 100:.0f}% capacity. "
                    f"It may become congested in the next 10 minutes."
                ),
                zone_id=zid,
                zone_name=zdata["name"],
                action=f"Consider leaving {zdata['name']} soon or plan an alternative route.",
                expires=10,
            ))

    # ── 2. Crowd surge prediction alerts ─────────────────────────────────
    # Detect rapid density increases by computing average positive delta
    # over the last 5 history snapshots.  A surge alert is triggered when
    # the average increase exceeds 3 percentage points AND the zone is
    # already above 60 % (to avoid false positives in empty zones).
    history: list = db.get("/stadium/history") or []
    if len(history) >= 5:
        for zid, zdata in zones.items():
            recent: List[float] = [
                h.get("zones", {}).get(zid, {}).get("density", 0)
                for h in history[-5:]
            ]
            if len(recent) >= 3:
                # Calculate per-step deltas and average the positive ones
                deltas: List[float] = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
                avg_increase: float = sum(d for d in deltas if d > 0) / max(1, len(deltas))

                # Threshold: >3 pp average increase + already above 60 %
                if avg_increase > 0.03 and zdata["current_density"] > 0.6:
                    predicted_pct: float = min(99, zdata["current_density"] * 100 + 15)
                    alerts.append(_build_alert(
                        severity="warning",
                        title=f"📈 Crowd surge detected at {zdata['name']}",
                        message=(
                            f"Crowd density at {zdata['name']} has been rising rapidly. "
                            f"Predicted to reach {predicted_pct:.0f}% in the next 10 minutes."
                        ),
                        zone_id=zid,
                        zone_name=zdata["name"],
                        action=f"Leave {zdata['name']} now to avoid the upcoming rush.",
                        expires=10,
                    ))

    # ── 3. Facility wait time alerts ─────────────────────────────────────
    # Facilities exceeding the critical wait threshold (20 min) get a
    # "try alternatives" recommendation.  Moderate waits (10+ min) get
    # an informational nudge.
    for _fid, fdata in facilities.items():
        wait: float = fdata["current_wait_minutes"]

        if wait >= settings.WAIT_CRITICAL_MINUTES:
            zone_name: str = zones.get(fdata["zone_id"], {}).get("name", "Unknown")
            alerts.append(_build_alert(
                severity="critical",
                title=f"🕐 Extremely long wait at {fdata['name']}",
                message=(
                    f"{fdata['name']} has a {wait:.0f}-minute wait. "
                    f"Consider alternatives nearby."
                ),
                zone_id=fdata["zone_id"],
                zone_name=zone_name,
                action=f"Try a different {fdata['facility_type'].replace('_', ' ')} with a shorter queue.",
                expires=8,
            ))
        elif wait >= settings.WAIT_WARNING_MINUTES:
            zone_name = zones.get(fdata["zone_id"], {}).get("name", "Unknown")
            alerts.append(_build_alert(
                severity="info",
                title=f"⏳ Moderate wait at {fdata['name']}",
                message=f"{fdata['name']} currently has a {wait:.0f}-minute wait.",
                zone_id=fdata["zone_id"],
                zone_name=zone_name,
                action="Check wait times for alternatives before heading over.",
                expires=15,
            ))

    # Sort by severity priority -- critical alerts surface first
    alerts.sort(key=lambda a: _SEVERITY_ORDER.get(a["severity"], 3))

    # Persist the latest alert set for the /alerts/history endpoint
    db.set("/stadium/alerts", alerts)

    # Publish critical alerts to Pub/Sub for downstream notification systems
    # (mobile push via FCM, SMS via Twilio, Slack webhooks, etc.)
    try:
        from app.services.pubsub_service import publish_alert
        for alert in alerts:
            if alert["severity"] == "critical":
                publish_alert(alert)
    except Exception:
        pass  # Pub/Sub publishing is best-effort

    return alerts


def get_alert_history() -> List[Dict[str, Any]]:
    """Return the most recently generated alert set from the mock DB.

    Returns:
        A list of alert dicts, or an empty list if no alerts have been
        generated yet.

    Complexity:
        Time:  O(S) where S = stored alert list size (deepcopy).
        Space: O(S).
    """
    return db.get("/stadium/alerts") or []


# ── Private Helpers ─────────────────────────────────────────────────────────


def _build_alert(
    *,
    severity: str,
    title: str,
    message: str,
    zone_id: str,
    zone_name: str,
    action: str,
    expires: int,
) -> Dict[str, Any]:
    """Construct a standardised alert dict.

    Args:
        severity: One of ``"critical"``, ``"warning"``, ``"info"``.
        title: Short alert headline (may include emoji).
        message: Detailed description with data-driven context.
        zone_id: Affected zone identifier.
        zone_name: Human-readable zone name.
        action: Recommended user action.
        expires: Minutes until this alert should be considered stale.

    Returns:
        A fully-populated alert dict with a generated ``alert_id``
        and current timestamp.
    """
    return {
        "alert_id": str(uuid.uuid4())[:8],
        "severity": severity,
        "title": title,
        "message": message,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "action": action,
        "timestamp": now_iso(),
        "expires_in_minutes": expires,
    }
