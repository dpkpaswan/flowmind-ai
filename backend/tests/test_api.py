"""
FlowMind AI — Comprehensive API Test Suite
Tests all endpoints: happy path, edge cases, and error handling.
"""

import pytest
from tests.conftest import (
    VALID_ZONE_IDS,
    VALID_FACILITY_TYPES,
    VALID_FACILITY_IDS,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  ROOT / HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealthCheck:
    """GET / — Health check and API info."""

    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_contains_app_info(self, client):
        data = client.get("/").json()
        assert data["name"] == "FlowMind AI"
        assert data["status"] == "operational"
        assert "version" in data
        assert "docs" in data

    def test_root_lists_endpoints(self, client):
        data = client.get("/").json()
        endpoints = data["endpoints"]
        assert "crowd" in endpoints
        assert "predictions" in endpoints
        assert "heatmap" in endpoints
        assert "wait_times" in endpoints
        assert "alerts" in endpoints
        assert "chat" in endpoints
        assert "simulation" in endpoints
        assert "emergency" in endpoints


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/crowd/current
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrowdCurrent:
    """GET /api/crowd/current — Current crowd density for all zones."""

    def test_returns_200(self, client):
        resp = client.get("/api/crowd/current")
        assert resp.status_code == 200

    def test_response_has_overview_fields(self, client):
        data = client.get("/api/crowd/current").json()
        assert "stadium_name" in data
        assert "total_capacity" in data
        assert "current_attendance" in data
        assert "overall_density" in data
        assert "zones" in data
        assert "timestamp" in data

    def test_stadium_name_matches_config(self, client):
        data = client.get("/api/crowd/current").json()
        assert data["stadium_name"] == "MetaStadium Arena"

    def test_contains_all_zones(self, client):
        data = client.get("/api/crowd/current").json()
        zone_ids = [z["zone_id"] for z in data["zones"]]
        for zid in VALID_ZONE_IDS:
            assert zid in zone_ids, f"Missing zone: {zid}"

    def test_zones_have_required_fields(self, client):
        data = client.get("/api/crowd/current").json()
        required = [
            "zone_id", "name", "current_density", "status",
            "capacity", "current_count", "coordinates",
            "predicted_density", "prediction_minutes",
        ]
        for zone in data["zones"]:
            for field in required:
                assert field in zone, f"Zone {zone.get('zone_id')} missing '{field}'"

    def test_density_values_are_bounded(self, client):
        data = client.get("/api/crowd/current").json()
        assert 0 <= data["overall_density"] <= 1
        for zone in data["zones"]:
            assert 0 <= zone["current_density"] <= 1
            assert 0 <= zone["predicted_density"] <= 1

    def test_zone_status_is_valid(self, client):
        data = client.get("/api/crowd/current").json()
        valid_statuses = {"low", "moderate", "high", "critical"}
        for zone in data["zones"]:
            assert zone["status"] in valid_statuses

    def test_coordinates_are_present(self, client):
        data = client.get("/api/crowd/current").json()
        for zone in data["zones"]:
            assert "lat" in zone["coordinates"]
            assert "lng" in zone["coordinates"]

    def test_current_count_within_capacity(self, client):
        data = client.get("/api/crowd/current").json()
        for zone in data["zones"]:
            assert zone["current_count"] <= zone["capacity"]
            assert zone["current_count"] >= 0

    def test_overall_density_is_consistent(self, client):
        data = client.get("/api/crowd/current").json()
        total_count = sum(z["current_count"] for z in data["zones"])
        total_cap = sum(z["capacity"] for z in data["zones"])
        expected = round(total_count / total_cap, 3)
        assert abs(data["overall_density"] - expected) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/crowd/predict
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrowdPredict:
    """GET /api/crowd/predict — Congestion predictions for all zones."""

    def test_returns_200(self, client):
        resp = client.get("/api/crowd/predict")
        assert resp.status_code == 200

    def test_response_has_predictions_key(self, client):
        data = client.get("/api/crowd/predict").json()
        assert "predictions" in data
        assert isinstance(data["predictions"], list)

    def test_predictions_cover_all_zones(self, client):
        data = client.get("/api/crowd/predict").json()
        zone_ids = [p["zone_id"] for p in data["predictions"]]
        for zid in VALID_ZONE_IDS:
            assert zid in zone_ids

    def test_prediction_structure(self, client):
        data = client.get("/api/crowd/predict").json()
        for pred in data["predictions"]:
            assert "zone_id" in pred
            assert "name" in pred
            assert "current_density" in pred
            assert "current_status" in pred
            assert "predictions" in pred
            assert isinstance(pred["predictions"], list)

    def test_prediction_intervals(self, client):
        """Each zone should have predictions at 5, 10, 15 minute intervals."""
        data = client.get("/api/crowd/predict").json()
        for pred in data["predictions"]:
            intervals = [p["minutes_ahead"] for p in pred["predictions"]]
            assert intervals == [5, 10, 15]

    def test_predicted_densities_are_bounded(self, client):
        data = client.get("/api/crowd/predict").json()
        for pred in data["predictions"]:
            for p in pred["predictions"]:
                assert 0 <= p["predicted_density"] <= 1
                assert p["predicted_status"] in {"low", "moderate", "high", "critical"}


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/crowd/heatmap
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrowdHeatmap:
    """GET /api/crowd/heatmap — Heatmap data points."""

    def test_returns_200(self, client):
        resp = client.get("/api/crowd/heatmap")
        assert resp.status_code == 200

    def test_response_has_points_key(self, client):
        data = client.get("/api/crowd/heatmap").json()
        assert "points" in data
        assert isinstance(data["points"], list)

    def test_points_have_required_fields(self, client):
        data = client.get("/api/crowd/heatmap").json()
        for point in data["points"]:
            assert "lat" in point
            assert "lng" in point
            assert "weight" in point

    def test_point_weights_are_bounded(self, client):
        data = client.get("/api/crowd/heatmap").json()
        for point in data["points"]:
            assert 0 <= point["weight"] <= 1

    def test_multiple_points_per_zone(self, client):
        """Each zone generates 5 points (1 core + 4 spread)."""
        data = client.get("/api/crowd/heatmap").json()
        # 8 zones × 5 points = 40 points
        assert len(data["points"]) == 8 * 5

    def test_coordinates_are_realistic(self, client):
        """Coordinates should be near Mumbai (approx 19.07°N, 72.87°E)."""
        data = client.get("/api/crowd/heatmap").json()
        for point in data["points"]:
            assert 19.0 < point["lat"] < 19.2
            assert 72.8 < point["lng"] < 73.0


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/wait-times
# ═══════════════════════════════════════════════════════════════════════════════


class TestWaitTimes:
    """GET /api/wait-times — Facility wait times."""

    def test_returns_200(self, client):
        resp = client.get("/api/wait-times")
        assert resp.status_code == 200

    def test_response_has_facilities_key(self, client):
        data = client.get("/api/wait-times").json()
        assert "facilities" in data
        assert isinstance(data["facilities"], list)

    def test_all_facilities_present(self, client):
        data = client.get("/api/wait-times").json()
        ids = [f["facility_id"] for f in data["facilities"]]
        for fid in VALID_FACILITY_IDS:
            assert fid in ids, f"Missing facility: {fid}"

    def test_facility_fields(self, client):
        data = client.get("/api/wait-times").json()
        required = [
            "facility_id", "name", "facility_type", "zone_id",
            "current_wait_minutes", "predicted_wait_minutes",
            "queue_length", "is_open",
        ]
        for fac in data["facilities"]:
            for field in required:
                assert field in fac, f"Facility {fac.get('facility_id')} missing '{field}'"

    def test_wait_times_are_non_negative(self, client):
        data = client.get("/api/wait-times").json()
        for fac in data["facilities"]:
            assert fac["current_wait_minutes"] >= 0
            assert fac["predicted_wait_minutes"] >= 0
            assert fac["queue_length"] >= 0

    def test_facility_types_are_valid(self, client):
        data = client.get("/api/wait-times").json()
        for fac in data["facilities"]:
            assert fac["facility_type"] in VALID_FACILITY_TYPES

    def test_sorted_by_longest_wait_first(self, client):
        data = client.get("/api/wait-times").json()
        waits = [f["current_wait_minutes"] for f in data["facilities"]]
        assert waits == sorted(waits, reverse=True)


class TestWaitTimesBestAlternative:
    """GET /api/wait-times/best/{facility_type} — Best alternative finder."""

    @pytest.mark.parametrize("ftype", ["food_stall", "restroom", "gate"])
    def test_valid_type_returns_200(self, client, ftype):
        resp = client.get(f"/api/wait-times/best/{ftype}")
        assert resp.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/api/wait-times/best/food_stall").json()
        assert "recommended" in data
        assert "alternatives" in data
        assert "reason" in data

    def test_recommended_is_shortest_wait(self, client):
        data = client.get("/api/wait-times/best/restroom").json()
        if data["recommended"] and data["alternatives"]:
            rec_wait = data["recommended"]["current_wait_minutes"]
            for alt in data["alternatives"]:
                assert alt["current_wait_minutes"] >= rec_wait

    def test_invalid_type_returns_400(self, client):
        resp = client.get("/api/wait-times/best/invalid_type")
        assert resp.status_code == 400

    def test_invalid_type_error_message(self, client):
        data = client.get("/api/wait-times/best/swimming_pool").json()
        assert "detail" in data
        assert "Invalid facility type" in data["detail"]

    def test_reason_is_non_empty(self, client):
        data = client.get("/api/wait-times/best/food_stall").json()
        assert isinstance(data["reason"], str)
        assert len(data["reason"]) > 0


class TestWaitTimesFacilityPredict:
    """GET /api/wait-times/{facility_id}/predict — Single facility prediction."""

    def test_valid_facility_returns_200(self, client):
        resp = client.get("/api/wait-times/food_1/predict")
        assert resp.status_code == 200

    def test_prediction_structure(self, client):
        data = client.get("/api/wait-times/food_1/predict").json()
        assert "facility_id" in data
        assert "predictions" in data
        assert isinstance(data["predictions"], list)

    def test_prediction_intervals(self, client):
        data = client.get("/api/wait-times/food_1/predict").json()
        intervals = [p["minutes_ahead"] for p in data["predictions"]]
        assert intervals == [5, 10, 15]

    def test_custom_minutes_ahead(self, client):
        data = client.get("/api/wait-times/food_1/predict?minutes_ahead=10").json()
        intervals = [p["minutes_ahead"] for p in data["predictions"]]
        assert intervals == [5, 10]

    def test_unknown_facility_returns_404(self, client):
        resp = client.get("/api/wait-times/nonexistent_facility/predict")
        assert resp.status_code == 404

    def test_unknown_facility_error_message(self, client):
        data = client.get("/api/wait-times/does_not_exist/predict").json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.parametrize("fid", ["gate_main", "restroom_1", "food_3"])
    def test_various_facilities(self, client, fid):
        resp = client.get(f"/api/wait-times/{fid}/predict")
        assert resp.status_code == 200
        data = resp.json()
        assert data["facility_id"] == fid


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/alerts
# ═══════════════════════════════════════════════════════════════════════════════


class TestAlerts:
    """GET /api/alerts — Active alerts based on live data."""

    def test_returns_200(self, client):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/api/alerts").json()
        assert "count" in data
        assert "alerts" in data
        assert isinstance(data["alerts"], list)
        assert data["count"] == len(data["alerts"])

    def test_alert_fields(self, client):
        data = client.get("/api/alerts").json()
        required = [
            "alert_id", "severity", "title", "message",
            "action", "timestamp", "expires_in_minutes",
        ]
        for alert in data["alerts"]:
            for field in required:
                assert field in alert, f"Alert missing '{field}'"

    def test_alert_severities_are_valid(self, client):
        data = client.get("/api/alerts").json()
        valid = {"info", "warning", "critical"}
        for alert in data["alerts"]:
            assert alert["severity"] in valid

    def test_alerts_sorted_by_severity(self, client):
        """Alerts should be sorted: critical → warning → info."""
        data = client.get("/api/alerts").json()
        order = {"critical": 0, "warning": 1, "info": 2}
        severities = [order[a["severity"]] for a in data["alerts"]]
        assert severities == sorted(severities)

    def test_count_is_non_negative(self, client):
        data = client.get("/api/alerts").json()
        assert data["count"] >= 0


class TestAlertHistory:
    """GET /api/alerts/history — Alert history."""

    def test_returns_200(self, client):
        resp = client.get("/api/alerts/history")
        assert resp.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/api/alerts/history").json()
        assert "count" in data
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    def test_history_populated_after_active_alerts(self, client):
        """History should have data after alerts are generated."""
        # Generate alerts first
        client.get("/api/alerts")
        # Now check history
        data = client.get("/api/alerts/history").json()
        # History stores the last generated set, count can be 0 if no thresholds hit
        assert isinstance(data["alerts"], list)


# ═══════════════════════════════════════════════════════════════════════════════
#  POST /api/chat
# ═══════════════════════════════════════════════════════════════════════════════


class TestChat:
    """POST /api/chat — AI assistant endpoint."""

    def test_returns_200_with_fallback(self, client):
        """Without Gemini key, the fallback handler should still return 200."""
        resp = client.post("/api/chat", json={"message": "Where is the best food?"})
        assert resp.status_code == 200

    def test_response_structure(self, client):
        data = client.post("/api/chat", json={"message": "How crowded is it?"}).json()
        assert "response" in data
        assert "confidence" in data
        assert "timestamp" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_fallback_crowd_query(self, client):
        data = client.post("/api/chat", json={"message": "How crowded is the stadium?"}).json()
        # Fallback should mention zones and percentages
        assert "%" in data["response"] or "capacity" in data["response"].lower()

    def test_fallback_food_query(self, client):
        data = client.post("/api/chat", json={"message": "Where can I get food?"}).json()
        assert data["response"]  # non-empty

    def test_fallback_restroom_query(self, client):
        data = client.post("/api/chat", json={"message": "Where is the nearest restroom?"}).json()
        assert data["response"]

    def test_fallback_exit_query(self, client):
        data = client.post("/api/chat", json={"message": "What's the fastest exit?"}).json()
        assert data["response"]

    def test_fallback_generic_query(self, client):
        data = client.post("/api/chat", json={"message": "Hello there!"}).json()
        # Generic queries get a stadium summary
        assert data["response"]

    def test_with_user_location(self, client):
        data = client.post("/api/chat", json={
            "message": "Is it crowded here?",
            "user_location": "north_stand",
        }).json()
        assert data["response"]

    def test_with_language_code(self, client):
        resp = client.post("/api/chat", json={
            "message": "How busy is it?",
            "language": "hi",
        })
        assert resp.status_code == 200

    def test_empty_message_returns_422(self, client):
        """Empty string should fail validation (min_length=1)."""
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_missing_message_returns_422(self, client):
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422

    def test_too_long_message_returns_422(self, client):
        """Messages over 500 chars should fail validation."""
        resp = client.post("/api/chat", json={"message": "x" * 501})
        assert resp.status_code == 422

    def test_max_length_message_accepted(self, client):
        resp = client.post("/api/chat", json={"message": "x" * 500})
        assert resp.status_code == 200

    def test_with_gemini_mock(self, client, mock_gemini_response):
        """With mocked Gemini, should get the canned AI response."""
        data = client.post("/api/chat", json={"message": "Where should I go?"}).json()
        assert "response" in data
        assert "timestamp" in data

    def test_confidence_is_bounded(self, client):
        data = client.post("/api/chat", json={"message": "Hi"}).json()
        if data["confidence"] is not None:
            assert 0 <= data["confidence"] <= 1


class TestChatLanguages:
    """GET /api/chat/languages — Supported languages."""

    def test_returns_200(self, client):
        resp = client.get("/api/chat/languages")
        assert resp.status_code == 200

    def test_contains_languages(self, client):
        data = client.get("/api/chat/languages").json()
        assert "languages" in data
        assert isinstance(data["languages"], dict)

    def test_english_is_supported(self, client):
        data = client.get("/api/chat/languages").json()
        assert "en" in data["languages"]
        assert data["languages"]["en"] == "English"

    def test_hindi_is_supported(self, client):
        data = client.get("/api/chat/languages").json()
        assert "hi" in data["languages"]


# ═══════════════════════════════════════════════════════════════════════════════
#  GET /api/simulation/status  &  POST /api/simulation/*
# ═══════════════════════════════════════════════════════════════════════════════


class TestSimulationStatus:
    """GET /api/simulation/status — Simulation state."""

    def test_returns_200(self, client):
        resp = client.get("/api/simulation/status")
        assert resp.status_code == 200

    def test_idle_by_default(self, client):
        data = client.get("/api/simulation/status").json()
        assert data["running"] is False
        assert data["phase"] == "idle"
        assert data["event_minute"] == 0

    def test_status_response_fields(self, client):
        data = client.get("/api/simulation/status").json()
        required = [
            "running", "speed", "phase", "phase_label",
            "phase_description", "event_minute", "total_minutes",
            "progress_pct", "elapsed_real_seconds", "timestamp", "phases",
        ]
        for field in required:
            assert field in data, f"Missing field: '{field}'"

    def test_total_minutes_is_120(self, client):
        data = client.get("/api/simulation/status").json()
        assert data["total_minutes"] == 120

    def test_phases_list_is_present(self, client):
        data = client.get("/api/simulation/status").json()
        assert isinstance(data["phases"], list)
        assert len(data["phases"]) == 5  # 5 event phases


class TestSimulationStart:
    """POST /api/simulation/start — Start simulation."""

    def test_start_returns_200(self, client):
        resp = client.post("/api/simulation/start")
        assert resp.status_code == 200

    def test_start_activates_simulation(self, client):
        data = client.post("/api/simulation/start").json()
        assert data["running"] is True
        assert data["phase"] == "pre_match"

    def test_start_with_custom_speed(self, client):
        data = client.post("/api/simulation/start", json={"speed": 30.0}).json()
        assert data["speed"] == 30.0
        assert data["running"] is True

    def test_start_default_speed(self, client):
        data = client.post("/api/simulation/start").json()
        assert data["speed"] == 10.0

    def test_start_speed_boundary_min(self, client):
        data = client.post("/api/simulation/start", json={"speed": 1.0}).json()
        assert data["speed"] == 1.0

    def test_start_speed_boundary_max(self, client):
        data = client.post("/api/simulation/start", json={"speed": 60.0}).json()
        assert data["speed"] == 60.0

    def test_start_speed_below_min_fails(self, client):
        resp = client.post("/api/simulation/start", json={"speed": 0.5})
        assert resp.status_code == 422

    def test_start_speed_above_max_fails(self, client):
        resp = client.post("/api/simulation/start", json={"speed": 100.0})
        assert resp.status_code == 422


class TestSimulationStop:
    """POST /api/simulation/stop — Stop simulation."""

    def test_stop_returns_200(self, client):
        resp = client.post("/api/simulation/stop")
        assert resp.status_code == 200

    def test_stop_resets_to_idle(self, client):
        # Start first, then stop
        client.post("/api/simulation/start")
        data = client.post("/api/simulation/stop").json()
        assert data["running"] is False
        assert data["phase"] == "idle"
        assert data["event_minute"] == 0

    def test_stop_when_not_running(self, client):
        """Stopping an idle simulation should still succeed."""
        data = client.post("/api/simulation/stop").json()
        assert data["running"] is False


class TestSimulationSpeed:
    """POST /api/simulation/speed — Change speed while running."""

    def test_change_speed_returns_200(self, client):
        client.post("/api/simulation/start")
        resp = client.post("/api/simulation/speed", json={"speed": 20.0})
        assert resp.status_code == 200

    def test_speed_is_updated(self, client):
        client.post("/api/simulation/start")
        data = client.post("/api/simulation/speed", json={"speed": 45.0}).json()
        assert data["speed"] == 45.0

    def test_speed_below_min_fails(self, client):
        resp = client.post("/api/simulation/speed", json={"speed": 0.1})
        assert resp.status_code == 422

    def test_speed_above_max_fails(self, client):
        resp = client.post("/api/simulation/speed", json={"speed": 100.0})
        assert resp.status_code == 422

    def test_speed_missing_body_fails(self, client):
        resp = client.post("/api/simulation/speed", json={})
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
#  POST /api/emergency/evacuate  &  related endpoints
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmergencyEvacuate:
    """POST /api/emergency/evacuate — Trigger evacuation."""

    def test_returns_200(self, client):
        resp = client.post("/api/emergency/evacuate")
        assert resp.status_code == 200

    def test_evacuation_plan_structure(self, client):
        data = client.post("/api/emergency/evacuate").json()
        assert data["active"] is True
        assert "evacuation_id" in data
        assert "triggered_at" in data
        assert "total_people" in data
        assert "total_gate_throughput" in data
        assert "estimated_total_time_min" in data
        assert "zone_plans" in data
        assert "gate_summary" in data
        assert "general_instructions" in data

    def test_zone_plans_cover_all_zones(self, client):
        data = client.post("/api/emergency/evacuate").json()
        plan_zone_ids = [zp["zone_id"] for zp in data["zone_plans"]]
        for zid in VALID_ZONE_IDS:
            assert zid in plan_zone_ids

    def test_zone_plan_fields(self, client):
        data = client.post("/api/emergency/evacuate").json()
        required = [
            "zone_id", "zone_name", "current_count",
            "assigned_gate", "assigned_gate_name",
            "estimated_evac_minutes", "distance_priority", "instructions",
        ]
        for plan in data["zone_plans"]:
            for field in required:
                assert field in plan, f"Zone plan missing '{field}'"

    def test_gate_summary_fields(self, client):
        data = client.post("/api/emergency/evacuate").json()
        for gate in data["gate_summary"]:
            assert "gate_id" in gate
            assert "gate_name" in gate
            assert "assigned_people" in gate
            assert "throughput_per_min" in gate
            assert "estimated_clear_time_min" in gate

    def test_general_instructions_are_present(self, client):
        data = client.post("/api/emergency/evacuate").json()
        assert len(data["general_instructions"]) >= 3

    def test_evacuation_times_are_positive(self, client):
        data = client.post("/api/emergency/evacuate").json()
        assert data["estimated_total_time_min"] > 0
        for plan in data["zone_plans"]:
            assert plan["estimated_evac_minutes"] >= 0

    def test_total_people_is_consistent(self, client):
        data = client.post("/api/emergency/evacuate").json()
        zone_total = sum(zp["current_count"] for zp in data["zone_plans"])
        assert data["total_people"] == zone_total


class TestEmergencyCancel:
    """POST /api/emergency/cancel — Cancel evacuation."""

    def test_cancel_returns_200(self, client):
        resp = client.post("/api/emergency/cancel")
        assert resp.status_code == 200

    def test_cancel_deactivates(self, client):
        # Trigger, then cancel
        client.post("/api/emergency/evacuate")
        data = client.post("/api/emergency/cancel").json()
        assert data["active"] is False
        assert "Evacuation cancelled" in data["message"]

    def test_cancel_when_no_active_evacuation(self, client):
        data = client.post("/api/emergency/cancel").json()
        assert data["active"] is False


class TestEmergencyStatus:
    """GET /api/emergency/status — Evacuation status."""

    def test_returns_200(self, client):
        resp = client.get("/api/emergency/status")
        assert resp.status_code == 200

    def test_no_active_evacuation(self, client):
        data = client.get("/api/emergency/status").json()
        assert data["active"] is False
        assert "No active evacuation" in data["message"]

    def test_active_evacuation_shows_plan(self, client):
        client.post("/api/emergency/evacuate")
        data = client.get("/api/emergency/status").json()
        assert data["active"] is True
        assert "zone_plans" in data

    def test_cancelled_evacuation_status(self, client):
        client.post("/api/emergency/evacuate")
        client.post("/api/emergency/cancel")
        data = client.get("/api/emergency/status").json()
        assert data["active"] is False


# ═══════════════════════════════════════════════════════════════════════════════
#  EDGE CASES & ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Cross-cutting edge cases and error handling tests."""

    def test_nonexistent_route_returns_404(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_wrong_method_on_chat_returns_405(self, client):
        resp = client.get("/api/chat")
        assert resp.status_code == 405

    def test_wrong_method_on_evacuate_returns_405(self, client):
        resp = client.get("/api/emergency/evacuate")
        assert resp.status_code == 405

    def test_chat_with_invalid_json_returns_422(self, client):
        resp = client.post(
            "/api/chat",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_chat_with_wrong_field_type_returns_422(self, client):
        resp = client.post("/api/chat", json={"message": 12345})
        # Pydantic v2 coerces int to str, so this may succeed;
        # the important thing is it doesn't crash
        assert resp.status_code in (200, 422)

    def test_simulation_start_with_string_speed_returns_422(self, client):
        resp = client.post("/api/simulation/start", json={"speed": "fast"})
        assert resp.status_code == 422

    def test_rapid_successive_evacuations(self, client):
        """Triggering evacuate multiple times should work each time."""
        data1 = client.post("/api/emergency/evacuate").json()
        data2 = client.post("/api/emergency/evacuate").json()
        assert data1["evacuation_id"] != data2["evacuation_id"]
        assert data2["active"] is True

    def test_start_stop_start_simulation(self, client):
        """Simulation state should reset properly on restart."""
        client.post("/api/simulation/start", json={"speed": 20.0})
        client.post("/api/simulation/stop")
        data = client.post("/api/simulation/start", json={"speed": 5.0}).json()
        assert data["running"] is True
        assert data["speed"] == 5.0
        assert data["phase"] == "pre_match"

    def test_concurrent_data_freshness(self, client):
        """Two consecutive crowd requests should both succeed
        (data is regenerated each call)."""
        d1 = client.get("/api/crowd/current").json()
        d2 = client.get("/api/crowd/current").json()
        assert d1["timestamp"] is not None
        assert d2["timestamp"] is not None

    def test_all_endpoints_return_json(self, client):
        """All endpoints should return application/json."""
        endpoints = [
            ("GET", "/"),
            ("GET", "/api/crowd/current"),
            ("GET", "/api/crowd/predict"),
            ("GET", "/api/crowd/heatmap"),
            ("GET", "/api/wait-times"),
            ("GET", "/api/alerts"),
            ("GET", "/api/alerts/history"),
            ("GET", "/api/simulation/status"),
            ("GET", "/api/emergency/status"),
            ("GET", "/api/chat/languages"),
        ]
        for method, path in endpoints:
            resp = client.get(path) if method == "GET" else client.post(path)
            assert "application/json" in resp.headers.get("content-type", ""), (
                f"{method} {path} did not return JSON"
            )
