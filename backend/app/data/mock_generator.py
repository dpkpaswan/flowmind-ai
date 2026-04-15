"""FlowMind AI -- Mock Stadium Data Generator.

Generates realistic, time-varying crowd and facility data for a sports
stadium.  Uses sine waves + noise to simulate event flow patterns:
    Pre-match buildup -> kickoff peak -> halftime dip -> second half -> exit surge

Performance notes:
    * ``generate_snapshot()`` is wrapped in a 10-second TTL cache so multiple
      callers within the same window get the same dict without re-computing.
      This is critical because the frontend polls /crowd/current, /alerts,
      /wait-times concurrently -- without caching, each request would trigger
      a separate O(Z + F) generation pass.
    * Cache invalidation is time-based: after 10 s the next call regenerates.
    * The background refresh task in main.py pre-warms the cache every 30 s.
"""

import math
import random
import time
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.data.firebase_client import db
from app.utils.helpers import clamp, density_to_status

__all__ = [
    "generate_snapshot",
    "invalidate_snapshot_cache",
    "get_zone_list",
    "get_facility_list",
    "ZONES",
    "FACILITIES",
]

# ── Stadium Layout Definition ───────────────────────────────────────────────
# Space: O(Z) where Z = number of zones (8).  Static; allocated once at import.

ZONES = [
    {
        "zone_id": "north_stand",
        "name": "North Stand",
        "capacity": 13000,
        "base_density": 0.55,
        "coordinates": {"lat": 19.0760, "lng": 72.8777},
    },
    {
        "zone_id": "south_stand",
        "name": "South Stand",
        "capacity": 13000,
        "base_density": 0.60,
        "coordinates": {"lat": 19.0740, "lng": 72.8777},
    },
    {
        "zone_id": "east_stand",
        "name": "East Stand",
        "capacity": 10000,
        "base_density": 0.50,
        "coordinates": {"lat": 19.0750, "lng": 72.8797},
    },
    {
        "zone_id": "west_stand",
        "name": "West Stand",
        "capacity": 10000,
        "base_density": 0.48,
        "coordinates": {"lat": 19.0750, "lng": 72.8757},
    },
    {
        "zone_id": "food_court_a",
        "name": "Food Court A",
        "capacity": 3000,
        "base_density": 0.70,
        "coordinates": {"lat": 19.0765, "lng": 72.8787},
    },
    {
        "zone_id": "food_court_b",
        "name": "Food Court B",
        "capacity": 3000,
        "base_density": 0.65,
        "coordinates": {"lat": 19.0735, "lng": 72.8767},
    },
    {
        "zone_id": "main_gate",
        "name": "Main Gate",
        "capacity": 6000,
        "base_density": 0.45,
        "coordinates": {"lat": 19.0730, "lng": 72.8777},
    },
    {
        "zone_id": "vip_lounge",
        "name": "VIP Lounge",
        "capacity": 2000,
        "base_density": 0.30,
        "coordinates": {"lat": 19.0770, "lng": 72.8767},
    },
]

# Space: O(F) where F = number of facilities (13).  Static; allocated once.
FACILITIES = [
    # Food stalls
    {"facility_id": "food_1", "name": "Burger Junction", "facility_type": "food_stall", "zone_id": "food_court_a", "base_wait": 8},
    {"facility_id": "food_2", "name": "Pizza Palace", "facility_type": "food_stall", "zone_id": "food_court_a", "base_wait": 10},
    {"facility_id": "food_3", "name": "Noodle Bar", "facility_type": "food_stall", "zone_id": "food_court_b", "base_wait": 6},
    {"facility_id": "food_4", "name": "Taco Stand", "facility_type": "food_stall", "zone_id": "food_court_b", "base_wait": 7},
    {"facility_id": "food_5", "name": "Drinks Corner", "facility_type": "food_stall", "zone_id": "food_court_a", "base_wait": 4},
    # Restrooms
    {"facility_id": "restroom_1", "name": "Restroom North", "facility_type": "restroom", "zone_id": "north_stand", "base_wait": 5},
    {"facility_id": "restroom_2", "name": "Restroom South", "facility_type": "restroom", "zone_id": "south_stand", "base_wait": 6},
    {"facility_id": "restroom_3", "name": "Restroom East", "facility_type": "restroom", "zone_id": "east_stand", "base_wait": 4},
    {"facility_id": "restroom_4", "name": "Restroom VIP", "facility_type": "restroom", "zone_id": "vip_lounge", "base_wait": 2},
    # Gates
    {"facility_id": "gate_main", "name": "Main Entrance", "facility_type": "gate", "zone_id": "main_gate", "base_wait": 12},
    {"facility_id": "gate_north", "name": "North Gate", "facility_type": "gate", "zone_id": "north_stand", "base_wait": 8},
    {"facility_id": "gate_south", "name": "South Gate", "facility_type": "gate", "zone_id": "south_stand", "base_wait": 9},
    {"facility_id": "gate_vip", "name": "VIP Entrance", "facility_type": "gate", "zone_id": "vip_lounge", "base_wait": 3},
]

# ── Time-based simulation ───────────────────────────────────────────────────

# We use `time.time()` as the clock to create smooth, continuous variation.
_start_time = time.time()


def _event_phase_multiplier() -> float:
    """
    Returns a multiplier (0.3 – 1.2) based on simulated event phase.
    Cycles through: calm -> buildup -> peak -> halftime_dip -> peak -> exit
    Full cycle = ~20 minutes (compressed for demo purposes).

    Time complexity:  O(1) — piecewise arithmetic + one sin() call.
    Space complexity: O(1).
    """
    elapsed = (time.time() - _start_time) % 1200  # 20-minute cycle
    phase = elapsed / 1200  # 0.0 to 1.0

    # Piecewise function to simulate event flow
    if phase < 0.1:        # Early arrival (calm)
        return 0.4 + phase * 3
    elif phase < 0.3:      # Buildup
        return 0.7 + (phase - 0.1) * 2.5
    elif phase < 0.5:      # First-half peak
        return 1.0 + math.sin(phase * math.pi * 4) * 0.15
    elif phase < 0.6:      # Halftime dip (food court surge)
        return 0.7 + math.sin(phase * math.pi * 2) * 0.1
    elif phase < 0.85:     # Second-half peak
        return 0.95 + math.sin(phase * math.pi * 3) * 0.2
    else:                  # Post-match exit surge
        return 1.1 - (phase - 0.85) * 4


def _zone_density(zone: Dict, phase_mult: float) -> float:
    """
    Calculate current density for a zone with time variation + noise.

    Time complexity:  O(1) — one sin() + one gauss() + arithmetic.
    Space complexity: O(1).
    """
    base = zone["base_density"]
    # Zone-specific wave (each zone oscillates slightly differently)
    zone_wave = math.sin(time.time() / 60 + hash(zone["zone_id"]) % 10) * 0.08
    noise = random.gauss(0, 0.03)
    density = base * phase_mult + zone_wave + noise
    return clamp(density, 0.05, 0.98)


def _facility_wait(facility: Dict, zone_density: float) -> float:
    """
    Calculate current wait time for a facility based on its zone's density.

    Time complexity:  O(1) — arithmetic + one gauss() call.
    Space complexity: O(1).
    """
    base = facility["base_wait"]
    # Wait scales with zone density (exponentially at high density)
    density_factor = 1 + (zone_density ** 2) * 3
    noise = random.gauss(0, 1.0)
    wait = base * density_factor + noise
    return max(0.5, round(wait, 1))


# ── Snapshot Cache ───────────────────────────────────────────────────────────
# Time-based LRU cache (TTL = 10 seconds).
#
# Why not functools.lru_cache?
#   lru_cache doesn't support TTL expiry.  We need the cache to auto-invalidate
#   after 10 s so that crowd data stays fresh, while still serving identical
#   results to concurrent requests within the same 10 s window.
#
# Thread safety:
#   A threading.Lock guards _snapshot_cache / _snapshot_timestamp so that
#   concurrent requests from the FastAPI threadpool don't race on read/write.
#
# Space complexity: O(Z + F) — one snapshot dict (≈8 zones + 13 facilities).
# Time complexity:  O(1) for cache hit, O(Z + F) for cache miss (regenerate).

_SNAPSHOT_CACHE_TTL = 10  # seconds
_snapshot_cache: Dict = {}
_snapshot_timestamp: float = 0.0
_snapshot_lock = threading.Lock()


# ── Public API ───────────────────────────────────────────────────────────────


def generate_snapshot() -> Dict:
    """
    Generate a complete stadium data snapshot and store it in the mock DB.
    Returns the full snapshot dict.

    Results are cached for 10 seconds.  Within that window, all callers
    (crowd router, alerts router, wait-times router, chat context builder)
    receive the same snapshot — eliminating redundant computation.

    Time complexity:
      - Cache hit:  O(1).
      - Cache miss: O(Z + F) where Z = |ZONES|, F = |FACILITIES|.
        Inner loops: Z density calcs + F wait calcs + F queue calcs.
    Space complexity: O(Z + F) for the cached snapshot dict.
    """
    global _snapshot_cache, _snapshot_timestamp

    # Fast path: return cached snapshot if still fresh
    now_mono = time.monotonic()
    if _snapshot_cache and (now_mono - _snapshot_timestamp) < _SNAPSHOT_CACHE_TTL:
        return _snapshot_cache

    with _snapshot_lock:
        # Double-check after acquiring lock (another thread may have refreshed)
        if _snapshot_cache and (time.monotonic() - _snapshot_timestamp) < _SNAPSHOT_CACHE_TTL:
            return _snapshot_cache

        snapshot = _generate_snapshot_impl()
        _snapshot_cache = snapshot
        _snapshot_timestamp = time.monotonic()
        return snapshot


def _generate_snapshot_impl() -> Dict:
    """
    Internal snapshot generation — always computes fresh data.
    Called only on cache miss (at most once per 10 s window).

    Time complexity:  O(Z + F) — one pass over zones, one pass over facilities.
    Space complexity: O(Z + F) — snapshot dict + zone_densities lookup dict.
    """
    # Check if event simulation is running — use its multiplier if so
    from app.services.simulation_service import get_simulation_phase_multiplier
    sim_mult = get_simulation_phase_multiplier()
    phase_mult = sim_mult if sim_mult is not None else _event_phase_multiplier()
    now = datetime.now(timezone.utc).isoformat()

    # Generate zone data — O(Z) where Z = len(ZONES) = 8
    zone_data = {}
    zone_densities = {}  # O(Z) lookup dict for facility wait calc

    for zone in ZONES:
        density = _zone_density(zone, phase_mult)
        zone_densities[zone["zone_id"]] = density
        current_count = int(density * zone["capacity"])

        zone_data[zone["zone_id"]] = {
            "zone_id": zone["zone_id"],
            "name": zone["name"],
            "current_density": round(density, 3),
            "status": density_to_status(density),
            "capacity": zone["capacity"],
            "current_count": current_count,
            "coordinates": zone["coordinates"],
        }

    # Generate facility wait times — O(F) where F = len(FACILITIES) = 13
    facility_data = {}
    for fac in FACILITIES:
        zone_density = zone_densities.get(fac["zone_id"], 0.5)  # O(1) dict lookup
        wait = _facility_wait(fac, zone_density)

        facility_data[fac["facility_id"]] = {
            "facility_id": fac["facility_id"],
            "name": fac["name"],
            "facility_type": fac["facility_type"],
            "zone_id": fac["zone_id"],
            "current_wait_minutes": wait,
            "queue_length": int(wait * random.uniform(1.5, 3.0)),
            "is_open": random.random() > 0.03,  # 3% chance closed
        }

    # Build snapshot — O(Z) summation
    total_count = sum(z["current_count"] for z in zone_data.values())
    total_capacity = sum(z["capacity"] for z in zone_data.values())

    snapshot = {
        "zones": zone_data,
        "facilities": facility_data,
        "overview": {
            "stadium_name": "MetaStadium Arena",
            "total_capacity": total_capacity,
            "current_attendance": total_count,
            "overall_density": round(total_count / total_capacity, 3),
            "phase_multiplier": round(phase_mult, 3),
            "timestamp": now,
        },
    }

    # Store in mock DB
    db.set("/stadium/current", snapshot)

    # Append to history (keep last 30 snapshots for trend analysis)
    # Space: O(H) where H = history length, capped at 30.
    history = db.get("/stadium/history") or []
    history.append({
        "zones": {zid: {"density": zd["current_density"]} for zid, zd in zone_data.items()},
        "overall_density": snapshot["overview"]["overall_density"],
        "timestamp": now,
    })
    if len(history) > 30:
        history = history[-30:]
    db.set("/stadium/history", history)

    # Log to BigQuery for long-term analytics (best-effort, non-blocking)
    try:
        from app.services.bigquery_service import log_crowd_snapshot
        log_crowd_snapshot(snapshot)
    except Exception:
        pass  # BigQuery logging is best-effort

    return snapshot


def invalidate_snapshot_cache() -> None:
    """
    Force-expire the snapshot cache.  Called by simulation_service when
    the simulation speed or state changes, ensuring the next request
    reflects the new simulation parameters immediately.

    Time complexity:  O(1).
    Space complexity: O(1).
    """
    global _snapshot_timestamp
    with _snapshot_lock:
        _snapshot_timestamp = 0.0


def get_zone_list() -> List[Dict]:
    """
    Return the static zone layout configuration.

    Time complexity:  O(1) — returns a reference to the module-level list.
    Space complexity: O(1) — no copy.
    """
    return ZONES


def get_facility_list() -> List[Dict]:
    """
    Return the static facility configuration.

    Time complexity:  O(1) — returns a reference to the module-level list.
    Space complexity: O(1) — no copy.
    """
    return FACILITIES
