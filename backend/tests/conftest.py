"""
FlowMind AI — Pytest Fixtures & Configuration
Shared fixtures for all API tests.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.data.firebase_client import MockFirebaseDB
from app.data.mock_generator import generate_snapshot


# ── Core Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def client():
    """
    A FastAPI TestClient scoped to the entire test session.
    Uses the real app with its lifespan events (initial data generation).
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fresh_client():
    """
    A fresh TestClient per test — use when you need isolated state
    (e.g., evacuation/simulation state tests).
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_simulation_state():
    """Reset simulation state before each test to avoid leaking state."""
    from app.services.simulation_service import _sim_state, _lock
    with _lock:
        _sim_state["running"] = False
        _sim_state["speed"] = 1.0
        _sim_state["phase"] = "idle"
        _sim_state["elapsed_real"] = 0
        _sim_state["elapsed_sim"] = 0
        _sim_state["start_time"] = None
        _sim_state["event_minute"] = 0
    yield


@pytest.fixture(autouse=True)
def _reset_evacuation_state():
    """Reset evacuation state before each test to avoid leaking state."""
    from app.services.evacuation_service import _evac_state
    _evac_state["active"] = False
    _evac_state["plan"] = None
    _evac_state["triggered_at"] = None
    yield


# ── Data Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def snapshot():
    """Generate and return a fresh stadium data snapshot."""
    return generate_snapshot()


@pytest.fixture()
def mock_gemini_response():
    """
    Patch the Gemini model so chat tests don't hit the real API.
    Returns a canned response that mimics Gemini's structure.
    """
    mock_response = MagicMock()
    mock_response.text = (
        "Head to North Stand — it's at 45% capacity right now, "
        "much less crowded than South Stand at 82%. "
        "I'd recommend grabbing food at Noodle Bar with only a 4 min wait."
    )

    mock_chat = AsyncMock()
    mock_chat.send_message_async = AsyncMock(return_value=mock_response)

    mock_model = MagicMock()
    mock_model.start_chat = MagicMock(return_value=mock_chat)

    with patch("app.services.gemini_service._get_model", return_value=mock_model):
        yield mock_model


# ── Helper Constants ─────────────────────────────────────────────────────────

VALID_ZONE_IDS = [
    "north_stand", "south_stand", "east_stand", "west_stand",
    "food_court_a", "food_court_b", "main_gate", "vip_lounge",
]

VALID_FACILITY_TYPES = ["food_stall", "restroom", "gate", "merchandise"]

VALID_FACILITY_IDS = [
    "food_1", "food_2", "food_3", "food_4", "food_5",
    "restroom_1", "restroom_2", "restroom_3", "restroom_4",
    "gate_main", "gate_north", "gate_south", "gate_vip",
]
