"""
FlowMind AI — Mock Stadium Data Generator
Generates realistic, time-varying crowd and facility data for a sports stadium.
Uses sine waves + noise to simulate event flow patterns:
  Pre-match buildup → kickoff peak → halftime dip → second-half → exit surge
"""

import math
import random
import time
from datetime import datetime, timezone
from typing import Dict, List

from app.data.firebase_client import db
from app.utils.helpers import clamp, density_to_status

# ── Stadium Layout Definition ───────────────────────────────────────────────

ZONES = [
    {
        "zone_id": "north_stand",
        "name": "North Stand",
        "capacity": 12000,
        "base_density": 0.55,
        "coordinates": {"lat": 19.0760, "lng": 72.8777},
    },
    {
        "zone_id": "south_stand",
        "name": "South Stand",
        "capacity": 12000,
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
        "capacity": 5000,
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
    Cycles through: calm → buildup → peak → halftime_dip → peak → exit
    Full cycle = ~20 minutes (compressed for demo purposes).
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
    """Calculate current density for a zone with time variation + noise."""
    base = zone["base_density"]
    # Zone-specific wave (each zone oscillates slightly differently)
    zone_wave = math.sin(time.time() / 60 + hash(zone["zone_id"]) % 10) * 0.08
    noise = random.gauss(0, 0.03)
    density = base * phase_mult + zone_wave + noise
    return clamp(density, 0.05, 0.98)


def _facility_wait(facility: Dict, zone_density: float) -> float:
    """Calculate current wait time for a facility based on its zone's density."""
    base = facility["base_wait"]
    # Wait scales with zone density (exponentially at high density)
    density_factor = 1 + (zone_density ** 2) * 3
    noise = random.gauss(0, 1.0)
    wait = base * density_factor + noise
    return max(0.5, round(wait, 1))


# ── Public API ───────────────────────────────────────────────────────────────


def generate_snapshot() -> Dict:
    """
    Generate a complete stadium data snapshot and store it in the mock DB.
    Returns the full snapshot dict.
    """
    # Check if event simulation is running — use its multiplier if so
    from app.services.simulation_service import get_simulation_phase_multiplier
    sim_mult = get_simulation_phase_multiplier()
    phase_mult = sim_mult if sim_mult is not None else _event_phase_multiplier()
    now = datetime.now(timezone.utc).isoformat()

    # Generate zone data
    zone_data = {}
    zone_densities = {}  # Cache for facility wait calc

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

    # Generate facility wait times
    facility_data = {}
    for fac in FACILITIES:
        zone_density = zone_densities.get(fac["zone_id"], 0.5)
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

    # Build snapshot
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
    history = db.get("/stadium/history") or []
    history.append({
        "zones": {zid: {"density": zd["current_density"]} for zid, zd in zone_data.items()},
        "overall_density": snapshot["overview"]["overall_density"],
        "timestamp": now,
    })
    if len(history) > 30:
        history = history[-30:]
    db.set("/stadium/history", history)

    return snapshot


def get_zone_list() -> List[Dict]:
    """Return the static zone layout configuration."""
    return ZONES


def get_facility_list() -> List[Dict]:
    """Return the static facility configuration."""
    return FACILITIES
