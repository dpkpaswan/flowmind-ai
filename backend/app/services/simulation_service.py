"""
FlowMind AI — Event Simulation Service
Controls the mock data generator's time phase to simulate a full match
in compressed time (90 min → configurable speed).
"""

import time
import threading
from typing import Dict, Optional
from app.utils.helpers import now_iso

# ── Simulation State ────────────────────────────────────────────────────────

_sim_state = {
    "running": False,
    "speed": 1.0,        # 1x = real-time, 10x = fast, 30x = demo mode
    "phase": "idle",     # idle, pre_match, first_half, halftime, second_half, post_match
    "elapsed_real": 0,   # real seconds elapsed since start
    "elapsed_sim": 0,    # simulated minutes elapsed
    "start_time": None,
    "event_minute": 0,   # match minute (0–90+)
}

_lock = threading.Lock()

# ── Event Timeline ──────────────────────────────────────────────────────────

EVENT_PHASES = [
    {"phase": "pre_match",    "start_min": 0,   "end_min": 15,  "label": "Pre-Match",      "description": "Fans arriving, gates busy, stands filling up"},
    {"phase": "first_half",   "start_min": 15,  "end_min": 60,  "label": "First Half",     "description": "Match underway, stands packed, food courts quieter"},
    {"phase": "halftime",     "start_min": 60,  "end_min": 75,  "label": "Halftime",       "description": "Rush to food courts and restrooms"},
    {"phase": "second_half",  "start_min": 75,  "end_min": 105, "label": "Second Half",    "description": "Fans back in stands, some early leavers"},
    {"phase": "post_match",   "start_min": 105, "end_min": 120, "label": "Post-Match",     "description": "Mass exodus, gates congested, all exits busy"},
]

TOTAL_EVENT_MINUTES = 120


def _get_phase_for_minute(minute: int) -> Dict:
    """Return the event phase for a given match minute."""
    for phase in EVENT_PHASES:
        if phase["start_min"] <= minute < phase["end_min"]:
            return phase
    return EVENT_PHASES[-1]  # post_match fallback


# ── Override for mock_generator ──────────────────────────────────────────────

def get_simulation_phase_multiplier() -> Optional[float]:
    """
    Returns a crowd density multiplier based on simulation state.
    Returns None if simulation is not running (use default behavior).
    Called by mock_generator to override its normal time-based calculation.
    """
    with _lock:
        if not _sim_state["running"]:
            return None

        minute = _sim_state["event_minute"]

        # Piecewise multiplier based on event phase
        if minute < 15:      # Pre-match: building up
            return 0.3 + (minute / 15) * 0.4
        elif minute < 60:    # First half: high, seated
            return 0.75 + ((minute - 15) / 45) * 0.15
        elif minute < 75:    # Halftime: surge to facilities
            return 0.85 + ((minute - 60) / 15) * 0.15
        elif minute < 105:   # Second half: high again
            return 0.80 + ((minute - 75) / 30) * 0.1
        else:                # Post-match: exit surge
            return 1.0 + ((minute - 105) / 15) * 0.15


# ── Public API ───────────────────────────────────────────────────────────────


def start_simulation(speed: float = 10.0) -> Dict:
    """Start or restart the event simulation at the given speed."""
    with _lock:
        _sim_state["running"] = True
        _sim_state["speed"] = max(1.0, min(60.0, speed))
        _sim_state["start_time"] = time.time()
        _sim_state["elapsed_real"] = 0
        _sim_state["elapsed_sim"] = 0
        _sim_state["event_minute"] = 0
        _sim_state["phase"] = "pre_match"

    return get_simulation_status()


def stop_simulation() -> Dict:
    """Stop the simulation and reset to idle."""
    with _lock:
        _sim_state["running"] = False
        _sim_state["phase"] = "idle"
        _sim_state["speed"] = 1.0
        _sim_state["event_minute"] = 0
        _sim_state["elapsed_sim"] = 0
        _sim_state["elapsed_real"] = 0
        _sim_state["start_time"] = None

    return get_simulation_status()


def set_simulation_speed(speed: float) -> Dict:
    """Change simulation speed while running."""
    with _lock:
        _sim_state["speed"] = max(1.0, min(60.0, speed))
    return get_simulation_status()


def get_simulation_status() -> Dict:
    """Get current simulation state, updating time calculations."""
    with _lock:
        if _sim_state["running"] and _sim_state["start_time"]:
            real_elapsed = time.time() - _sim_state["start_time"]
            sim_minutes = (real_elapsed * _sim_state["speed"]) / 60.0

            # Cap at total event duration
            if sim_minutes >= TOTAL_EVENT_MINUTES:
                sim_minutes = TOTAL_EVENT_MINUTES
                _sim_state["running"] = False
                _sim_state["phase"] = "completed"

            _sim_state["elapsed_real"] = real_elapsed
            _sim_state["elapsed_sim"] = sim_minutes
            _sim_state["event_minute"] = int(sim_minutes)

            if _sim_state["phase"] != "completed":
                phase_info = _get_phase_for_minute(int(sim_minutes))
                _sim_state["phase"] = phase_info["phase"]

        # Build response
        phase_info = _get_phase_for_minute(_sim_state["event_minute"])
        progress = min(100, (_sim_state["event_minute"] / TOTAL_EVENT_MINUTES) * 100)

        return {
            "running": _sim_state["running"],
            "speed": _sim_state["speed"],
            "phase": _sim_state["phase"],
            "phase_label": phase_info["label"] if _sim_state["phase"] != "idle" else "Idle",
            "phase_description": phase_info["description"] if _sim_state["phase"] != "idle" else "Simulation not started",
            "event_minute": _sim_state["event_minute"],
            "total_minutes": TOTAL_EVENT_MINUTES,
            "progress_pct": round(progress, 1),
            "elapsed_real_seconds": round(_sim_state["elapsed_real"], 1),
            "timestamp": now_iso(),
            "phases": EVENT_PHASES,
        }
