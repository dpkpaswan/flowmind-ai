"""
FlowMind AI — Emergency Evacuation Service
Calculates optimal exit routes and gate assignments for each zone
when an emergency evacuation is triggered.
"""

import uuid
from typing import Dict, List

from app.data.firebase_client import db
from app.data.mock_generator import generate_snapshot, ZONES, FACILITIES
from app.utils.helpers import now_iso

# ── Gate-to-Zone Proximity Map ──────────────────────────────────────────────
# Defines the closest gates for each zone, ordered by proximity.

ZONE_EXIT_MAP = {
    "north_stand":  ["gate_north", "gate_main", "gate_vip"],
    "south_stand":  ["gate_south", "gate_main"],
    "east_stand":   ["gate_north", "gate_south", "gate_main"],
    "west_stand":   ["gate_south", "gate_north", "gate_main"],
    "food_court_a": ["gate_north", "gate_main", "gate_vip"],
    "food_court_b": ["gate_south", "gate_main"],
    "main_gate":    ["gate_main", "gate_south", "gate_north"],
    "vip_lounge":   ["gate_vip", "gate_north"],
}

# Gate capacities (people per minute throughput)
GATE_THROUGHPUT = {
    "gate_main":  250,
    "gate_north": 180,
    "gate_south": 180,
    "gate_vip":   80,
}

# ── Evacuation State ────────────────────────────────────────────────────────

_evac_state = {
    "active": False,
    "plan": None,
    "triggered_at": None,
}


def trigger_evacuation() -> Dict:
    """
    Calculate and return an optimal evacuation plan.
    Assigns each zone to the best available gate based on:
    - Proximity (closest gate first)
    - Current gate congestion
    - Gate throughput capacity
    - Zone crowd count
    """
    snapshot = generate_snapshot()
    zones_data = snapshot["zones"]
    facilities_data = snapshot["facilities"]

    # Track how many people are assigned to each gate
    gate_load = {gid: 0 for gid in GATE_THROUGHPUT}

    zone_plans = []

    # Sort zones by crowd count (most crowded first = highest priority)
    sorted_zones = sorted(
        zones_data.values(),
        key=lambda z: z["current_count"],
        reverse=True,
    )

    for zone in sorted_zones:
        zid = zone["zone_id"]
        count = zone["current_count"]
        possible_gates = ZONE_EXIT_MAP.get(zid, ["gate_main"])

        # Score each gate: lower = better
        gate_scores = []
        for gid in possible_gates:
            throughput = GATE_THROUGHPUT.get(gid, 100)
            current_load = gate_load[gid]
            current_wait = facilities_data.get(gid, {}).get("current_wait_minutes", 5)

            # Score = (existing load / throughput) + proximity_penalty + current_wait
            proximity_idx = possible_gates.index(gid)
            score = (current_load / throughput) + (proximity_idx * 0.3) + (current_wait * 0.1)
            gate_scores.append((gid, score, throughput))

        # Assign to lowest-score gate
        gate_scores.sort(key=lambda x: x[1])
        assigned_gate_id = gate_scores[0][0]
        assigned_throughput = gate_scores[0][2]

        gate_load[assigned_gate_id] += count

        # Calculate estimated evacuation time
        total_at_gate = gate_load[assigned_gate_id]
        evac_time_minutes = round(total_at_gate / assigned_throughput, 1)

        # Get gate name
        gate_info = facilities_data.get(assigned_gate_id, {})
        gate_name = gate_info.get("name", assigned_gate_id.replace("_", " ").title())

        zone_plans.append({
            "zone_id": zid,
            "zone_name": zone["name"],
            "current_count": count,
            "assigned_gate": assigned_gate_id,
            "assigned_gate_name": gate_name,
            "estimated_evac_minutes": evac_time_minutes,
            "distance_priority": possible_gates.index(assigned_gate_id) + 1,
            "instructions": _build_instructions(zone["name"], gate_name, evac_time_minutes),
        })

    # Sort plans by zone name for consistent display
    zone_plans.sort(key=lambda z: z["zone_name"])

    # Gate summary
    gate_summary = []
    for gid, load in gate_load.items():
        gate_info = facilities_data.get(gid, {})
        throughput = GATE_THROUGHPUT[gid]
        gate_summary.append({
            "gate_id": gid,
            "gate_name": gate_info.get("name", gid.replace("_", " ").title()),
            "assigned_people": load,
            "throughput_per_min": throughput,
            "estimated_clear_time_min": round(load / throughput, 1) if load > 0 else 0,
            "load_pct": round((load / throughput) * 10, 1),  # relative load indicator
        })

    total_people = sum(z["current_count"] for z in zones_data.values())
    total_throughput = sum(GATE_THROUGHPUT.values())
    overall_evac_time = round(total_people / total_throughput, 1)

    plan = {
        "evacuation_id": str(uuid.uuid4())[:8],
        "active": True,
        "triggered_at": now_iso(),
        "total_people": total_people,
        "total_gate_throughput": total_throughput,
        "estimated_total_time_min": overall_evac_time,
        "zone_plans": zone_plans,
        "gate_summary": gate_summary,
        "general_instructions": [
            "REMAIN CALM. Follow the assigned exit directions.",
            "Do NOT run. Walk briskly toward your designated gate.",
            "Help those around you who may need assistance.",
            "Leave all personal belongings if they slow you down.",
            "Follow staff instructions at all times.",
        ],
    }

    _evac_state["active"] = True
    _evac_state["plan"] = plan
    _evac_state["triggered_at"] = now_iso()

    return plan


def cancel_evacuation() -> Dict:
    """Cancel an active evacuation."""
    _evac_state["active"] = False
    _evac_state["plan"] = None
    return {"active": False, "message": "Evacuation cancelled.", "timestamp": now_iso()}


def get_evacuation_status() -> Dict:
    """Get current evacuation status."""
    if _evac_state["active"] and _evac_state["plan"]:
        return _evac_state["plan"]
    return {"active": False, "message": "No active evacuation.", "timestamp": now_iso()}


def _build_instructions(zone_name: str, gate_name: str, evac_time: float) -> str:
    """Build human-readable evacuation instruction for a zone."""
    if evac_time < 5:
        urgency = "Proceed calmly"
    elif evac_time < 10:
        urgency = "Move promptly"
    else:
        urgency = "Evacuate immediately"

    return f"{urgency} from {zone_name} to {gate_name}. Estimated time: {evac_time} minutes."
