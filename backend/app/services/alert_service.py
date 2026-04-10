"""
FlowMind AI — Smart Alert Service
Generates actionable alerts based on crowd density and wait time thresholds.
"""

import uuid
from typing import Dict, List

from app.data.firebase_client import db
from app.data.mock_generator import generate_snapshot
from app.config import settings
from app.utils.helpers import now_iso, density_to_status


def generate_alerts() -> List[Dict]:
    """
    Scan current stadium data and generate smart alerts.
    Returns a list of active alerts sorted by severity.
    """
    snapshot = generate_snapshot()
    zones = snapshot["zones"]
    facilities = snapshot["facilities"]
    alerts = []

    # ── Zone-based density alerts ────────────────────────────────────────
    for zid, zdata in zones.items():
        density = zdata["current_density"]

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

    # ── Crowd surge prediction alerts ────────────────────────────────────
    history = db.get("/stadium/history") or []
    if len(history) >= 5:
        for zid, zdata in zones.items():
            recent = [
                h.get("zones", {}).get(zid, {}).get("density", 0)
                for h in history[-5:]
            ]
            if len(recent) >= 3:
                # Check for rapid increase trend
                deltas = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
                avg_increase = sum(d for d in deltas if d > 0) / max(1, len(deltas))

                if avg_increase > 0.03 and zdata["current_density"] > 0.6:
                    alerts.append(_build_alert(
                        severity="warning",
                        title=f"📈 Crowd surge detected at {zdata['name']}",
                        message=(
                            f"Crowd density at {zdata['name']} has been rising rapidly. "
                            f"Predicted to reach {min(99, zdata['current_density'] * 100 + 15):.0f}% "
                            f"in the next 10 minutes."
                        ),
                        zone_id=zid,
                        zone_name=zdata["name"],
                        action=f"Leave {zdata['name']} now to avoid the upcoming rush.",
                        expires=10,
                    ))

    # ── Wait time alerts ─────────────────────────────────────────────────
    for fid, fdata in facilities.items():
        wait = fdata["current_wait_minutes"]

        if wait >= settings.WAIT_CRITICAL_MINUTES:
            zone_name = zones.get(fdata["zone_id"], {}).get("name", "Unknown")
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

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

    # Store alerts in mock DB
    db.set("/stadium/alerts", alerts)

    return alerts


def get_alert_history() -> List[Dict]:
    """Return recent alert history from the mock DB."""
    return db.get("/stadium/alerts") or []


def _build_alert(
    severity: str,
    title: str,
    message: str,
    zone_id: str,
    zone_name: str,
    action: str,
    expires: int,
) -> Dict:
    """Helper to construct an alert dict."""
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
