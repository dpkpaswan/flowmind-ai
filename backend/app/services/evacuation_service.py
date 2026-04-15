"""FlowMind AI — Emergency Evacuation Service.

Calculates optimal exit routes and gate assignments for each stadium zone
when an emergency evacuation is triggered.  The optimiser considers:

    * **Proximity** — zones are assigned to their nearest gates first.
    * **Gate throughput** — higher-capacity gates absorb more evacuees.
    * **Current congestion** — already-busy gates are penalised.
    * **Load balancing** — cumulative gate load is tracked to spread
      evacuees across all available exits.

The algorithm processes zones in descending crowd-count order so that
the most-packed zones get priority access to the best gates.
"""

import uuid
from typing import Any, Dict, List

from app.data.mock_generator import generate_snapshot, ZONES, FACILITIES
from app.exceptions import EvacuationError
from app.utils.helpers import now_iso

__all__ = [
    "trigger_evacuation",
    "cancel_evacuation",
    "get_evacuation_status",
]

# ── Gate-to-Zone Proximity Map ──────────────────────────────────────────────
# Each zone lists its exit gates in order of physical proximity.
# The first gate in the list is the closest; the last is the farthest.

ZONE_EXIT_MAP: Dict[str, List[str]] = {
    "north_stand":  ["gate_north", "gate_main", "gate_vip"],
    "south_stand":  ["gate_south", "gate_main"],
    "east_stand":   ["gate_north", "gate_south", "gate_main"],
    "west_stand":   ["gate_south", "gate_north", "gate_main"],
    "food_court_a": ["gate_north", "gate_main", "gate_vip"],
    "food_court_b": ["gate_south", "gate_main"],
    "main_gate":    ["gate_main", "gate_south", "gate_north"],
    "vip_lounge":   ["gate_vip", "gate_north"],
}

# Gate capacities — people per minute throughput
GATE_THROUGHPUT: Dict[str, int] = {
    "gate_main":  250,
    "gate_north": 180,
    "gate_south": 180,
    "gate_vip":   80,
}

# ── Evacuation State ────────────────────────────────────────────────────────
# Module-level mutable state.  In a production system this would be
# backed by a distributed store; here it's adequate for single-instance
# Cloud Run deployments.

_evac_state: Dict[str, Any] = {
    "active": False,
    "plan": None,
    "triggered_at": None,
}


def trigger_evacuation() -> Dict[str, Any]:
    """Calculate and activate an optimal evacuation plan.

    The algorithm:
        1. Snapshot current stadium data.
        2. Sort zones by crowd count (highest first = highest priority).
        3. For each zone, score candidate gates using a composite metric
           of (load / throughput) + proximity penalty + current wait.
        4. Assign the zone to the lowest-scoring (best) gate.
        5. Accumulate gate load so subsequent zones see updated scores.

    Returns:
        The full evacuation plan dict with zone assignments, gate
        summary, and general instructions.

    Raises:
        EvacuationError: If snapshot data is unavailable or incomplete.

    Complexity:
        Time:  O(Z · G) where Z = zones, G = gates per zone (≤ 3).
        Space: O(Z + G) for the plan dicts.
    """
    try:
        snapshot: Dict[str, Any] = generate_snapshot()
    except Exception as exc:
        raise EvacuationError(
            "Cannot generate evacuation plan: snapshot unavailable.",
            details={"original_error": str(exc)},
        ) from exc

    zones_data: Dict[str, Dict] = snapshot["zones"]
    facilities_data: Dict[str, Dict] = snapshot["facilities"]

    # Track cumulative people assigned to each gate (for load-balancing)
    gate_load: Dict[str, int] = {gid: 0 for gid in GATE_THROUGHPUT}

    zone_plans: List[Dict[str, Any]] = []

    # Process zones in descending crowd-count order so the busiest
    # zones get first pick of the least-loaded gates
    sorted_zones: List[Dict] = sorted(
        zones_data.values(),
        key=lambda z: z["current_count"],
        reverse=True,
    )

    for zone in sorted_zones:
        zid: str = zone["zone_id"]
        count: int = zone["current_count"]
        possible_gates: List[str] = ZONE_EXIT_MAP.get(zid, ["gate_main"])

        # Score each candidate gate — lower score = better assignment
        gate_scores: List[tuple] = []
        for gid in possible_gates:
            throughput: int = GATE_THROUGHPUT.get(gid, 100)
            current_load: int = gate_load[gid]
            current_wait: float = facilities_data.get(gid, {}).get("current_wait_minutes", 5)

            # Composite score:
            #   - (load / throughput): penalises already-loaded gates
            #   - proximity_idx * 0.3: penalises farther gates
            #   - current_wait * 0.1: penalises congested gates
            proximity_idx: int = possible_gates.index(gid)
            score: float = (current_load / throughput) + (proximity_idx * 0.3) + (current_wait * 0.1)
            gate_scores.append((gid, score, throughput))

        # Assign to the gate with the lowest composite score
        gate_scores.sort(key=lambda x: x[1])
        assigned_gate_id: str = gate_scores[0][0]
        assigned_throughput: int = gate_scores[0][2]

        gate_load[assigned_gate_id] += count

        # Estimated evacuation time = total people at gate / throughput
        total_at_gate: int = gate_load[assigned_gate_id]
        evac_time_minutes: float = round(total_at_gate / assigned_throughput, 1)

        # Resolve gate display name
        gate_info: Dict = facilities_data.get(assigned_gate_id, {})
        gate_name: str = gate_info.get("name", assigned_gate_id.replace("_", " ").title())

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

    # Sort zone plans alphabetically for consistent UI display
    zone_plans.sort(key=lambda z: z["zone_name"])

    # Gate summary — shows how the evacuee load is distributed
    gate_summary: List[Dict[str, Any]] = []
    for gid, load in gate_load.items():
        gate_info = facilities_data.get(gid, {})
        throughput: int = GATE_THROUGHPUT[gid]
        gate_summary.append({
            "gate_id": gid,
            "gate_name": gate_info.get("name", gid.replace("_", " ").title()),
            "assigned_people": load,
            "throughput_per_min": throughput,
            "estimated_clear_time_min": round(load / throughput, 1) if load > 0 else 0,
            "load_pct": round((load / throughput) * 10, 1),
        })

    # Overall stats
    total_people: int = sum(z["current_count"] for z in zones_data.values())
    total_throughput: int = sum(GATE_THROUGHPUT.values())
    overall_evac_time: float = round(total_people / total_throughput, 1)

    plan: Dict[str, Any] = {
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

    # Persist evacuation state
    _evac_state["active"] = True
    _evac_state["plan"] = plan
    _evac_state["triggered_at"] = now_iso()

    # Publish evacuation plan to Pub/Sub for downstream emergency systems
    # (mobile push via FCM, digital signage activation, emergency services)
    try:
        from app.services.pubsub_service import publish_evacuation_event
        publish_evacuation_event(plan)
    except Exception:
        pass  # Pub/Sub is best-effort; evacuation proceeds regardless

    return plan


def cancel_evacuation() -> Dict[str, Any]:
    """Cancel an active evacuation and reset state.

    Returns:
        A confirmation dict with ``active=False`` and a timestamp.
    """
    _evac_state["active"] = False
    _evac_state["plan"] = None
    return {"active": False, "message": "Evacuation cancelled.", "timestamp": now_iso()}


def get_evacuation_status() -> Dict[str, Any]:
    """Get the current evacuation status.

    Returns:
        The active evacuation plan if one exists, otherwise a dict
        with ``active=False``.
    """
    if _evac_state["active"] and _evac_state["plan"]:
        return _evac_state["plan"]
    return {"active": False, "message": "No active evacuation.", "timestamp": now_iso()}


# ── Private Helpers ─────────────────────────────────────────────────────────


def _build_instructions(zone_name: str, gate_name: str, evac_time: float) -> str:
    """Build a human-readable evacuation instruction for a zone.

    The urgency level is determined by the estimated evacuation time:
        * < 5 min  → "Proceed calmly"
        * 5–10 min → "Move promptly"
        * > 10 min → "Evacuate immediately"

    Args:
        zone_name: Human-readable zone name (e.g. ``"North Stand"``).
        gate_name: Human-readable gate name (e.g. ``"North Gate"``).
        evac_time: Estimated evacuation time in minutes.

    Returns:
        A single-sentence instruction string.
    """
    urgency: str
    if evac_time < 5:
        urgency = "Proceed calmly"
    elif evac_time < 10:
        urgency = "Move promptly"
    else:
        urgency = "Evacuate immediately"

    return f"{urgency} from {zone_name} to {gate_name}. Estimated time: {evac_time} minutes."
