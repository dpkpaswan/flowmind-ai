"""FlowMind AI -- Google Cloud Monitoring Service.

Publishes custom metrics to Google Cloud Monitoring for real-time
dashboards and alerting policies.  Tracks:

    * ``custom.googleapis.com/flowmind/crowd_density`` -- per-zone density
    * ``custom.googleapis.com/flowmind/wait_time`` -- per-facility wait
    * ``custom.googleapis.com/flowmind/api_latency`` -- endpoint latency
    * ``custom.googleapis.com/flowmind/active_alerts`` -- alert count

Falls back to local metric logging when Cloud Monitoring is unavailable.
"""

import logging
import time
import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("flowmind.monitoring")

__all__ = [
    "record_metric",
    "record_api_latency",
    "record_crowd_density",
    "record_wait_time",
    "get_local_metrics_summary",
]

# ── Cloud Monitoring Client (lazy) ──────────────────────────────────────────

_monitoring_client: Optional[Any] = None
_monitoring_available: Optional[bool] = None


def _get_monitoring_client() -> Optional[Any]:
    """Lazy-initialise the Cloud Monitoring client.

    Returns:
        A ``monitoring_v3.MetricServiceClient``, or ``None`` if unavailable.
    """
    global _monitoring_client, _monitoring_available

    if _monitoring_available is False:
        return None
    if _monitoring_client is not None:
        return _monitoring_client

    try:
        from google.cloud import monitoring_v3

        _monitoring_client = monitoring_v3.MetricServiceClient()
        _monitoring_available = True
        logger.info("Cloud Monitoring client initialised.")
        return _monitoring_client
    except Exception as exc:
        _monitoring_available = False
        logger.info("Cloud Monitoring unavailable (%s) -> using local metrics.", type(exc).__name__)
        return None


# ── Local Metrics Store (in-memory fallback) ────────────────────────────────
# Stores the last N values for each metric so we can compute summaries
# even without Cloud Monitoring.  Thread-safe via lock.

_MAX_LOCAL_SAMPLES: int = 1000
_local_metrics: Dict[str, List[float]] = defaultdict(list)
_metrics_lock: threading.Lock = threading.Lock()


def _store_local(metric_name: str, value: float) -> None:
    """Store a metric value in the local in-memory ring buffer.

    Args:
        metric_name: Metric key (e.g. ``"api_latency"``).
        value: The metric value.
    """
    with _metrics_lock:
        buffer = _local_metrics[metric_name]
        buffer.append(value)
        # Ring buffer: keep only the last N samples
        if len(buffer) > _MAX_LOCAL_SAMPLES:
            _local_metrics[metric_name] = buffer[-_MAX_LOCAL_SAMPLES:]


# ── Public API ──────────────────────────────────────────────────────────────


def record_metric(metric_type: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """Record a custom metric to Cloud Monitoring.

    If Cloud Monitoring is unavailable, the metric is stored locally
    and logged at DEBUG level.

    Args:
        metric_type: Short metric name (e.g. ``"crowd_density"``).
            Will be prefixed with ``custom.googleapis.com/flowmind/``.
        value: The metric value (float).
        labels: Optional label key-value pairs for metric dimensions.

    Complexity:
        Time:  O(1) for local storage; O(network) for Cloud Monitoring.
        Space: O(1) per call.
    """
    full_type: str = f"custom.googleapis.com/flowmind/{metric_type}"
    label_key: str = f"{metric_type}:{','.join(f'{k}={v}' for k, v in (labels or {}).items())}"
    _store_local(label_key, value)

    client = _get_monitoring_client()
    if client is None:
        return

    project = settings.GOOGLE_CLOUD_PROJECT
    if not project:
        return

    try:
        from google.cloud import monitoring_v3
        from google.protobuf import timestamp_pb2
        import datetime

        project_name = f"projects/{project}"
        series = monitoring_v3.TimeSeries()
        series.metric.type = full_type
        series.resource.type = "global"
        series.resource.labels["project_id"] = project

        # Attach labels
        for k, v in (labels or {}).items():
            series.metric.labels[k] = v

        # Create a data point
        now = datetime.datetime.now(datetime.timezone.utc)
        interval = monitoring_v3.TimeInterval()
        interval.end_time = timestamp_pb2.Timestamp(
            seconds=int(now.timestamp()),
            nanos=int((now.timestamp() % 1) * 1e9),
        )
        point = monitoring_v3.Point(interval=interval)
        point.value.double_value = value
        series.points = [point]

        client.create_time_series(name=project_name, time_series=[series])
    except Exception as exc:
        logger.debug("Cloud Monitoring write failed: %s", exc)


def record_api_latency(endpoint: str, duration_ms: float) -> None:
    """Record API endpoint latency.

    Args:
        endpoint: The API path (e.g. ``"/api/crowd/current"``).
        duration_ms: Response time in milliseconds.
    """
    record_metric("api_latency", duration_ms, labels={"endpoint": endpoint})


def record_crowd_density(zone_id: str, density: float) -> None:
    """Record a zone's crowd density for monitoring dashboards.

    Args:
        zone_id: Zone identifier (e.g. ``"north_stand"``).
        density: Current density value (0.0--1.0).
    """
    record_metric("crowd_density", density, labels={"zone_id": zone_id})


def record_wait_time(facility_id: str, wait_minutes: float) -> None:
    """Record a facility's wait time for monitoring dashboards.

    Args:
        facility_id: Facility identifier (e.g. ``"food_1"``).
        wait_minutes: Current wait time in minutes.
    """
    record_metric("wait_time", wait_minutes, labels={"facility_id": facility_id})


def get_local_metrics_summary() -> Dict[str, Any]:
    """Get a summary of locally-stored metrics.

    Useful for the ``/health`` endpoint and debugging when Cloud
    Monitoring is not available.

    Returns:
        A dict mapping metric names to ``{count, min, max, avg}`` summaries.
    """
    with _metrics_lock:
        summary: Dict[str, Any] = {}
        for key, values in _local_metrics.items():
            if values:
                summary[key] = {
                    "count": len(values),
                    "min": round(min(values), 3),
                    "max": round(max(values), 3),
                    "avg": round(sum(values) / len(values), 3),
                }
        return summary
