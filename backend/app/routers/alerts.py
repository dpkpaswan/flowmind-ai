"""
FlowMind AI — Smart Alerts Router
Endpoints for active alerts and alert history.
"""

from fastapi import APIRouter

from app.services.alert_service import generate_alerts, get_alert_history

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("")
async def active_alerts():
    """
    Get current active alerts based on live crowd and wait time data.
    Alerts are generated fresh each call and sorted by severity.
    """
    alerts = generate_alerts()
    return {
        "count": len(alerts),
        "alerts": alerts,
    }


@router.get("/history")
async def alert_history():
    """
    Get recent alert history (last generated set).
    """
    history = get_alert_history()
    return {
        "count": len(history),
        "alerts": history,
    }
