"""FlowMind AI -- Google Cloud Pub/Sub Notification Service.

Publishes crowd events and alerts to Google Cloud Pub/Sub topics,
enabling downstream systems (Cloud Functions, real-time dashboards,
mobile push notifications) to react to stadium events in near real-time.

Topics:
    * ``flowmind-crowd-events`` -- Published on every snapshot generation.
    * ``flowmind-alerts``       -- Published when critical alerts are triggered.

Falls back to local logging when Pub/Sub is unavailable.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("flowmind.pubsub")

__all__ = [
    "publish_crowd_event",
    "publish_alert",
    "publish_evacuation_event",
]

# ── Pub/Sub Client (lazy) ───────────────────────────────────────────────────

_publisher: Optional[Any] = None
_pubsub_available: Optional[bool] = None

# Topic names
_CROWD_TOPIC: str = "flowmind-crowd-events"
_ALERTS_TOPIC: str = "flowmind-alerts"
_EVACUATION_TOPIC: str = "flowmind-evacuation"


def _get_publisher() -> Optional[Any]:
    """Lazy-initialise the Pub/Sub publisher client.

    Returns:
        A ``pubsub_v1.PublisherClient``, or ``None`` if unavailable.
    """
    global _publisher, _pubsub_available

    if _pubsub_available is False:
        return None
    if _publisher is not None:
        return _publisher

    try:
        from google.cloud import pubsub_v1

        _publisher = pubsub_v1.PublisherClient()
        _pubsub_available = True
        logger.info("Pub/Sub publisher client initialised.")
        return _publisher
    except Exception as exc:
        _pubsub_available = False
        logger.info("Pub/Sub unavailable (%s) -> events are logged locally only.", type(exc).__name__)
        return None


def _get_topic_path(topic_id: str) -> Optional[str]:
    """Build the full topic path for the configured GCP project.

    Args:
        topic_id: Short topic name (e.g. ``"flowmind-crowd-events"``).

    Returns:
        Full topic path, or ``None`` if project is not configured.
    """
    project: str = settings.GOOGLE_CLOUD_PROJECT
    if not project:
        return None

    publisher = _get_publisher()
    if publisher is None:
        return None

    return publisher.topic_path(project, topic_id)


def _publish(topic_id: str, data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> bool:
    """Publish a message to a Pub/Sub topic.

    The message data is JSON-serialised.  If Pub/Sub is unavailable,
    the event is logged locally at INFO level so data is not lost.

    Args:
        topic_id: Short topic name.
        data: Message payload dict (JSON-serialisable).
        attributes: Optional message attributes for filtering.

    Returns:
        ``True`` if published successfully, ``False`` otherwise.
    """
    topic_path = _get_topic_path(topic_id)
    publisher = _get_publisher()

    if topic_path is None or publisher is None:
        # Fallback: log the event locally
        logger.info("pubsub_event topic=%s data_keys=%s", topic_id, list(data.keys()))
        return False

    try:
        message_bytes: bytes = json.dumps(data, default=str).encode("utf-8")
        future = publisher.publish(
            topic_path,
            data=message_bytes,
            **(attributes or {}),
        )
        # Don't block on the future -- fire-and-forget for performance
        future.add_done_callback(
            lambda f: logger.debug("Published to %s: %s", topic_id, f.result()) if not f.exception() else
            logger.warning("Pub/Sub publish failed for %s: %s", topic_id, f.exception())
        )
        return True
    except Exception as exc:
        logger.warning("Pub/Sub publish error for %s: %s", topic_id, exc)
        return False


# ── Public API ──────────────────────────────────────────────────────────────


def publish_crowd_event(snapshot: Dict[str, Any]) -> bool:
    """Publish a crowd density snapshot to the crowd-events topic.

    Downstream consumers (Cloud Functions, BigQuery streaming inserts,
    real-time dashboards) receive the full snapshot for processing.

    Args:
        snapshot: The stadium snapshot dict from ``generate_snapshot()``.

    Returns:
        ``True`` if published, ``False`` if unavailable (logged locally).
    """
    overview = snapshot.get("overview", {})
    # Publish a summary to keep message size manageable (<10 KB)
    event: Dict[str, Any] = {
        "event_type": "crowd_snapshot",
        "stadium_name": overview.get("stadium_name", ""),
        "overall_density": overview.get("overall_density", 0),
        "current_attendance": overview.get("current_attendance", 0),
        "total_capacity": overview.get("total_capacity", 0),
        "phase_multiplier": overview.get("phase_multiplier", 0),
        "timestamp": overview.get("timestamp", ""),
        "zones": {
            zid: {
                "density": zdata.get("current_density", 0),
                "count": zdata.get("current_count", 0),
                "status": zdata.get("status", ""),
            }
            for zid, zdata in snapshot.get("zones", {}).items()
        },
    }
    return _publish(_CROWD_TOPIC, event, attributes={"event_type": "crowd_snapshot"})


def publish_alert(alert: Dict[str, Any]) -> bool:
    """Publish a critical alert to the alerts topic.

    Cloud Functions can subscribe to trigger:
        * Mobile push notifications via FCM
        * SMS alerts via Twilio
        * Slack/Teams webhook notifications

    Args:
        alert: The alert dict from ``_build_alert()``.

    Returns:
        ``True`` if published, ``False`` if unavailable.
    """
    return _publish(
        _ALERTS_TOPIC,
        alert,
        attributes={
            "severity": alert.get("severity", "info"),
            "zone_id": alert.get("zone_id", ""),
        },
    )


def publish_evacuation_event(plan: Dict[str, Any]) -> bool:
    """Publish an evacuation plan to the evacuation topic.

    Critical for triggering emergency response workflows:
        * Notify all connected mobile clients via FCM
        * Activate digital signage displays
        * Alert emergency services via integration

    Args:
        plan: The evacuation plan dict from ``trigger_evacuation()``.

    Returns:
        ``True`` if published, ``False`` if unavailable.
    """
    return _publish(
        _EVACUATION_TOPIC,
        plan,
        attributes={"event_type": "evacuation", "active": str(plan.get("active", False))},
    )
