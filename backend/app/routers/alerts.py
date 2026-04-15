"""FlowMind AI — Smart Alerts Router.

Endpoints for active alerts and alert history.
"""

from typing import Any, Dict

from fastapi import APIRouter

from app.services.alert_service import generate_alerts, get_alert_history

__all__ = ["router"]

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("")
async def active_alerts() -> Dict[str, Any]:
    """Get current active alerts based on live crowd and wait time data.

    Alerts are generated fresh each call and sorted by severity
    (critical → warning → info).

    Returns:
        A dict with ``count`` and ``alerts`` list.
    """
    alerts = generate_alerts()
    return {
        "count": len(alerts),
        "alerts": alerts,
    }


@router.get("/history")
async def alert_history() -> Dict[str, Any]:
    """Get recent alert history (last generated set).

    Returns:
        A dict with ``count`` and ``alerts`` list.
    """
    history = get_alert_history()
    return {
        "count": len(history),
        "alerts": history,
    }
