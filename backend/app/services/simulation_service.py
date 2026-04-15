"""FlowMind AI — Event Simulation Service.

Controls the mock data generator's time-phase multiplier to simulate a
full 120-minute football match in compressed real-time.  The simulation
cycles through five phases (pre-match → first half → halftime → second
half → post-match) and adjusts crowd density multipliers accordingly.

The simulation state is thread-safe (guarded by ``threading.Lock``)
because it is read by ``mock_generator.generate_snapshot()`` on every
snapshot tick and written by the simulation API endpoints.
"""

import time
import threading
from typing import Any, Dict, List, Optional

from app.exceptions import SimulationStateError
from app.utils.helpers import now_iso

__all__ = [
    "start_simulation",
    "stop_simulation",
    "set_simulation_speed",
    "get_simulation_status",
    "get_simulation_phase_multiplier",
]

# ── Simulation State ────────────────────────────────────────────────────────
# Mutable dict protected by ``_lock``.  All public functions acquire the
# lock before reading or writing.

_sim_state: Dict[str, Any] = {
    "running": False,
    "speed": 1.0,        # 1x = real-time, 10x = fast, 30x = demo mode
    "phase": "idle",     # idle | pre_match | first_half | halftime | second_half | post_match | completed
    "elapsed_real": 0,   # real seconds elapsed since start
    "elapsed_sim": 0,    # simulated minutes elapsed
    "start_time": None,  # time.time() when simulation was started
    "event_minute": 0,   # match minute (0–120)
}

_lock: threading.Lock = threading.Lock()

# ── Event Timeline ──────────────────────────────────────────────────────────
# Each phase defines a match-minute range and a description displayed in
# the frontend progress bar and status panel.

EVENT_PHASES: List[Dict[str, Any]] = [
    {"phase": "pre_match",    "start_min": 0,   "end_min": 15,  "label": "Pre-Match",      "description": "Fans arriving, gates busy, stands filling up"},
    {"phase": "first_half",   "start_min": 15,  "end_min": 60,  "label": "First Half",     "description": "Match underway, stands packed, food courts quieter"},
    {"phase": "halftime",     "start_min": 60,  "end_min": 75,  "label": "Halftime",       "description": "Rush to food courts and restrooms"},
    {"phase": "second_half",  "start_min": 75,  "end_min": 105, "label": "Second Half",    "description": "Fans back in stands, some early leavers"},
    {"phase": "post_match",   "start_min": 105, "end_min": 120, "label": "Post-Match",     "description": "Mass exodus, gates congested, all exits busy"},
]

TOTAL_EVENT_MINUTES: int = 120


# ── Private Helpers ─────────────────────────────────────────────────────────


def _get_phase_for_minute(minute: int) -> Dict[str, Any]:
    """Return the event phase dict for a given match minute.

    Args:
        minute: Simulated match minute (0–120).

    Returns:
        The matching phase dict from ``EVENT_PHASES``, or the last
        phase (post-match) as a fallback.

    Complexity:
        Time:  O(P) where P = len(EVENT_PHASES) = 5.
        Space: O(1).
    """
    for phase in EVENT_PHASES:
        if phase["start_min"] <= minute < phase["end_min"]:
            return phase
    # Past the end → post-match
    return EVENT_PHASES[-1]


# ── Override for mock_generator ──────────────────────────────────────────────


def get_simulation_phase_multiplier() -> Optional[float]:
    """Return a crowd-density multiplier based on the current simulation state.

    Called by ``mock_generator.generate_snapshot()`` on every snapshot
    tick.  When the simulation is running, this overrides the default
    time-based phase multiplier with a piecewise function tied to
    the simulated match minute.

    Returns:
        A float multiplier (0.3–1.15), or ``None`` if the simulation
        is idle (in which case the default multiplier is used).

    Complexity:
        Time:  O(1) — arithmetic only (lock acquisition amortised).
        Space: O(1).
    """
    with _lock:
        if not _sim_state["running"]:
            return None

        minute: int = _sim_state["event_minute"]

        # Piecewise density multiplier matching the event timeline:
        #   Pre-match (0–15):   ramp from 0.3 to 0.7  (fans trickling in)
        #   First half (15–60): ramp from 0.75 to 0.90 (seated, watching)
        #   Halftime (60–75):   ramp from 0.85 to 1.0  (rush to food/restrooms)
        #   Second half (75–105): ramp from 0.80 to 0.90 (some leave early)
        #   Post-match (105–120): ramp from 1.0 to 1.15 (mass exit)
        if minute < 15:
            return 0.3 + (minute / 15) * 0.4
        elif minute < 60:
            return 0.75 + ((minute - 15) / 45) * 0.15
        elif minute < 75:
            return 0.85 + ((minute - 60) / 15) * 0.15
        elif minute < 105:
            return 0.80 + ((minute - 75) / 30) * 0.1
        else:
            return 1.0 + ((minute - 105) / 15) * 0.15


# ── Public API ───────────────────────────────────────────────────────────────


def start_simulation(speed: float = 10.0) -> Dict[str, Any]:
    """Start (or restart) the event simulation at the given speed.

    Args:
        speed: Time multiplier.  ``1.0`` = real-time (120 min),
            ``10.0`` = demo mode (~12 min), ``60.0`` = ultra-fast (~2 min).
            Clamped to [1.0, 60.0].

    Returns:
        The current simulation status dict (same as ``get_simulation_status()``).
    """
    with _lock:
        _sim_state["running"] = True
        _sim_state["speed"] = max(1.0, min(60.0, speed))
        _sim_state["start_time"] = time.time()
        _sim_state["elapsed_real"] = 0
        _sim_state["elapsed_sim"] = 0
        _sim_state["event_minute"] = 0
        _sim_state["phase"] = "pre_match"

    return get_simulation_status()


def stop_simulation() -> Dict[str, Any]:
    """Stop the simulation and reset all state to idle.

    Returns:
        The current simulation status dict (phase will be ``"idle"``).
    """
    with _lock:
        _sim_state["running"] = False
        _sim_state["phase"] = "idle"
        _sim_state["speed"] = 1.0
        _sim_state["event_minute"] = 0
        _sim_state["elapsed_sim"] = 0
        _sim_state["elapsed_real"] = 0
        _sim_state["start_time"] = None

    return get_simulation_status()


def set_simulation_speed(speed: float) -> Dict[str, Any]:
    """Change simulation speed while the sim is running.

    Args:
        speed: New speed multiplier, clamped to [1.0, 60.0].

    Returns:
        The current simulation status dict.

    Raises:
        SimulationStateError: If the simulation is not currently running.
    """
    with _lock:
        if not _sim_state["running"]:
            raise SimulationStateError(
                "Cannot change speed: simulation is not running.",
                details={"current_phase": _sim_state["phase"]},
            )
        _sim_state["speed"] = max(1.0, min(60.0, speed))
    return get_simulation_status()


def get_simulation_status() -> Dict[str, Any]:
    """Get current simulation state, recalculating elapsed times.

    The simulated match minute is derived from wall-clock time elapsed
    since ``start_simulation()`` was called, multiplied by the speed
    factor.  When the simulated time exceeds ``TOTAL_EVENT_MINUTES``
    the simulation auto-completes.

    Returns:
        A dict containing ``running``, ``speed``, ``phase``,
        ``event_minute``, ``progress_pct``, and the full ``phases``
        timeline for frontend rendering.
    """
    with _lock:
        if _sim_state["running"] and _sim_state["start_time"]:
            # Calculate how many simulated minutes have elapsed
            real_elapsed: float = time.time() - _sim_state["start_time"]
            sim_minutes: float = (real_elapsed * _sim_state["speed"]) / 60.0

            # Auto-complete when the full event duration is reached
            if sim_minutes >= TOTAL_EVENT_MINUTES:
                sim_minutes = TOTAL_EVENT_MINUTES
                _sim_state["running"] = False
                _sim_state["phase"] = "completed"

            _sim_state["elapsed_real"] = real_elapsed
            _sim_state["elapsed_sim"] = sim_minutes
            _sim_state["event_minute"] = int(sim_minutes)

            # Update the current phase label based on simulated minute
            if _sim_state["phase"] != "completed":
                phase_info: Dict[str, Any] = _get_phase_for_minute(int(sim_minutes))
                _sim_state["phase"] = phase_info["phase"]

        # Build the response payload
        phase_info = _get_phase_for_minute(_sim_state["event_minute"])
        progress: float = min(100, (_sim_state["event_minute"] / TOTAL_EVENT_MINUTES) * 100)

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
