"""FlowMind AI — BigQuery Analytics Service.

Logs crowd events to a BigQuery dataset for historical analytics,
trend analysis, and offline model training.  Each stadium snapshot
generates one row per zone in the ``crowd_events`` table.

Falls back to local logging when BigQuery credentials are unavailable.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("flowmind.bigquery")

__all__ = [
    "log_crowd_snapshot",
    "query_crowd_history",
]

# ── BigQuery Client (lazy-initialized) ──────────────────────────────────────

_bq_client = None
_bq_available = None  # None = not yet checked, True/False = result


def _get_client() -> Optional[Any]:
    """Lazy-initialise the BigQuery client.

    Returns:
        A ``google.cloud.bigquery.Client`` instance, or ``None`` if
        BigQuery is unavailable (missing credentials or SDK).
    """
    global _bq_client, _bq_available

    if _bq_available is False:
        return None
    if _bq_client is not None:
        return _bq_client

    try:
        from google.cloud import bigquery

        project = settings.GOOGLE_CLOUD_PROJECT or None
        _bq_client = bigquery.Client(project=project)
        _bq_available = True
        logger.info("BigQuery client initialized (project=%s)", project)
        return _bq_client
    except Exception as exc:
        _bq_available = False
        logger.warning(
            "BigQuery unavailable (%s) -> events will only be logged locally.",
            type(exc).__name__,
        )
        return None


# ── Dataset / Table helpers ─────────────────────────────────────────────────

DATASET_ID = settings.BIGQUERY_DATASET
CROWD_EVENTS_TABLE = f"{DATASET_ID}.crowd_events"


def _ensure_table(client: Any) -> bool:
    """Create the ``crowd_events`` table if it does not exist.

    The schema mirrors the row dicts produced by ``log_crowd_snapshot()``.
    The table is day-partitioned on the ``timestamp`` column for
    efficient time-range queries.

    Args:
        client: An initialised ``bigquery.Client`` instance.

    Returns:
        ``True`` if the table is ready for inserts, ``False`` on failure.
    """
    from google.cloud import bigquery as bq

    table_ref = client.dataset(DATASET_ID).table("crowd_events")

    try:
        client.get_table(table_ref)
        return True
    except Exception:
        pass  # table doesn't exist yet

    schema = [
        bq.SchemaField("event_id", "STRING", mode="REQUIRED"),
        bq.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bq.SchemaField("zone_id", "STRING", mode="REQUIRED"),
        bq.SchemaField("zone_name", "STRING"),
        bq.SchemaField("current_density", "FLOAT"),
        bq.SchemaField("current_count", "INTEGER"),
        bq.SchemaField("capacity", "INTEGER"),
        bq.SchemaField("status", "STRING"),
        bq.SchemaField("phase_multiplier", "FLOAT"),
        bq.SchemaField("overall_density", "FLOAT"),
        bq.SchemaField("total_attendance", "INTEGER"),
    ]

    table = bq.Table(table_ref, schema=schema)
    table.time_partitioning = bq.TimePartitioning(
        type_=bq.TimePartitioningType.DAY,
        field="timestamp",
    )

    try:
        client.create_table(table)
        logger.info("Created BigQuery table %s.crowd_events", DATASET_ID)
        return True
    except Exception as exc:
        logger.error("Failed to create BigQuery table: %s", exc)
        return False


# ── Public API ──────────────────────────────────────────────────────────────


def log_crowd_snapshot(snapshot: Dict) -> bool:
    """
    Log a full stadium snapshot to BigQuery.
    Each zone becomes one row in the crowd_events table.

    Args:
        snapshot: The dict returned by ``generate_snapshot()``.

    Returns:
        True if rows were inserted, False otherwise (incl. fallback).
    """
    import uuid

    now = datetime.now(timezone.utc).isoformat()
    overview = snapshot.get("overview", {})
    zones = snapshot.get("zones", {})

    rows: List[Dict] = []
    for zone_id, zdata in zones.items():
        rows.append({
            "event_id": str(uuid.uuid4()),
            "timestamp": now,
            "zone_id": zone_id,
            "zone_name": zdata.get("name", zone_id),
            "current_density": zdata.get("current_density", 0),
            "current_count": zdata.get("current_count", 0),
            "capacity": zdata.get("capacity", 0),
            "status": zdata.get("status", "unknown"),
            "phase_multiplier": overview.get("phase_multiplier", 0),
            "overall_density": overview.get("overall_density", 0),
            "total_attendance": overview.get("current_attendance", 0),
        })

    client = _get_client()

    if client is None:
        # Fallback: log a summary locally so data isn't silently lost
        logger.info(
            "crowd_snapshot zones=%d attendance=%s density=%.1f%%",
            len(rows),
            overview.get("current_attendance", "?"),
            overview.get("overall_density", 0) * 100,
        )
        return False

    # Ensure the destination table exists
    if not _ensure_table(client):
        return False

    project = client.project
    full_table = f"{project}.{CROWD_EVENTS_TABLE}"

    try:
        errors = client.insert_rows_json(full_table, rows)
        if errors:
            logger.error("BigQuery insert errors: %s", errors)
            return False
        logger.info("Logged %d crowd rows to BigQuery", len(rows))
        return True
    except Exception as exc:
        logger.error("BigQuery insert failed: %s", exc)
        return False


def query_crowd_history(
    zone_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 500,
) -> List[Dict]:
    """
    Query recent crowd events from BigQuery.

    Args:
        zone_id: Optional zone filter.
        hours:   Look-back window in hours (default 24).
        limit:   Max rows to return.

    Returns:
        List of row dicts, or empty list on failure.
    """
    client = _get_client()
    if client is None:
        return []

    project = client.project
    full_table = f"{project}.{CROWD_EVENTS_TABLE}"

    sql = f"""
        SELECT *
        FROM `{full_table}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
    """
    params = [{"name": "hours", "parameterType": {"type": "INT64"}, "parameterValue": {"value": str(hours)}}]

    if zone_id:
        sql += " AND zone_id = @zone_id"
        params.append({
            "name": "zone_id",
            "parameterType": {"type": "STRING"},
            "parameterValue": {"value": zone_id},
        })

    sql += " ORDER BY timestamp DESC LIMIT @limit"
    params.append({
        "name": "limit",
        "parameterType": {"type": "INT64"},
        "parameterValue": {"value": str(limit)},
    })

    try:
        from google.cloud import bigquery as bq

        job_config = bq.QueryJobConfig(
            query_parameters=[
                bq.ScalarQueryParameter("hours", "INT64", hours),
                bq.ScalarQueryParameter("zone_id", "STRING", zone_id) if zone_id else None,
                bq.ScalarQueryParameter("limit", "INT64", limit),
            ]
        )
        # Filter out None params
        job_config.query_parameters = [p for p in job_config.query_parameters if p is not None]

        result = client.query(sql, job_config=job_config).result()
        return [dict(row) for row in result]
    except Exception as exc:
        logger.error("BigQuery query failed: %s", exc)
        return []
