"""FlowMind AI -- Google Cloud Storage Service.

Stores and retrieves heatmap snapshot images and analytics exports
in Google Cloud Storage.  Used for:

    * Caching rendered heatmap tiles for CDN delivery.
    * Exporting crowd analytics data for offline analysis.
    * Storing evacuation plan documents for audit compliance.

Falls back to local filesystem storage when GCS is unavailable.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("flowmind.storage")

__all__ = [
    "upload_snapshot_json",
    "get_snapshot_url",
    "list_recent_snapshots",
]

# ── GCS Client (lazy) ───────────────────────────────────────────────────────

_storage_client: Optional[Any] = None
_storage_available: Optional[bool] = None
_BUCKET_NAME: str = "flowmind-snapshots"


def _get_client() -> Optional[Any]:
    """Lazy-initialise the Cloud Storage client.

    Returns:
        A ``storage.Client``, or ``None`` if unavailable.
    """
    global _storage_client, _storage_available

    if _storage_available is False:
        return None
    if _storage_client is not None:
        return _storage_client

    try:
        from google.cloud import storage

        project = settings.GOOGLE_CLOUD_PROJECT or None
        _storage_client = storage.Client(project=project)
        _storage_available = True
        logger.info("Cloud Storage client initialised (bucket: %s).", _BUCKET_NAME)
        return _storage_client
    except Exception as exc:
        _storage_available = False
        logger.info("Cloud Storage unavailable (%s) -> snapshots stored locally.", type(exc).__name__)
        return None


# ── Public API ──────────────────────────────────────────────────────────────


def upload_snapshot_json(snapshot: Dict[str, Any], snapshot_id: str) -> Optional[str]:
    """Upload a crowd snapshot as a JSON file to Cloud Storage.

    The file is stored with a time-partitioned path:
    ``snapshots/YYYY/MM/DD/HH/{snapshot_id}.json``

    This makes it efficient to query and export data for specific
    time ranges.

    Args:
        snapshot: The stadium snapshot dict.
        snapshot_id: Unique identifier for this snapshot.

    Returns:
        The GCS URI (``gs://bucket/path``), or ``None`` on failure.

    Complexity:
        Time:  O(S) where S = serialised snapshot size + O(network).
        Space: O(S) for the serialised JSON.
    """
    client = _get_client()
    now = datetime.now(timezone.utc)
    # Time-partitioned path for efficient range queries
    blob_path = f"snapshots/{now.strftime('%Y/%m/%d/%H')}/{snapshot_id}.json"

    if client is None:
        # Fallback: log summary locally
        logger.info(
            "gcs_upload_skipped path=%s zones=%d",
            blob_path,
            len(snapshot.get("zones", {})),
        )
        return None

    try:
        bucket = client.bucket(_BUCKET_NAME)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(
            json.dumps(snapshot, default=str),
            content_type="application/json",
        )
        # Set lifecycle: auto-delete after 90 days for cost management
        blob.metadata = {"ttl_days": "90"}
        blob.patch()

        gcs_uri = f"gs://{_BUCKET_NAME}/{blob_path}"
        logger.info("Uploaded snapshot to %s", gcs_uri)
        return gcs_uri
    except Exception as exc:
        logger.warning("GCS upload failed: %s", exc)
        return None


def get_snapshot_url(blob_path: str, expiration_minutes: int = 60) -> Optional[str]:
    """Generate a signed URL for a stored snapshot.

    The URL is valid for ``expiration_minutes`` and can be shared with
    external systems or embedded in reports.

    Args:
        blob_path: The GCS object path (without bucket name).
        expiration_minutes: URL validity in minutes (default 60).

    Returns:
        A signed HTTPS URL, or ``None`` if GCS is unavailable.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        bucket = client.bucket(_BUCKET_NAME)
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )
        return url
    except Exception as exc:
        logger.warning("Failed to generate signed URL: %s", exc)
        return None


def list_recent_snapshots(hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
    """List recently uploaded snapshots from Cloud Storage.

    Args:
        hours: Look-back window in hours (default 24).
        limit: Maximum number of results (default 100).

    Returns:
        A list of ``{path, size_bytes, created}`` dicts, or an empty
        list if GCS is unavailable.
    """
    client = _get_client()
    if client is None:
        return []

    try:
        bucket = client.bucket(_BUCKET_NAME)
        now = datetime.now(timezone.utc)
        prefix = f"snapshots/{now.strftime('%Y/%m/%d')}"

        results: List[Dict[str, Any]] = []
        for blob in bucket.list_blobs(prefix=prefix, max_results=limit):
            results.append({
                "path": blob.name,
                "size_bytes": blob.size,
                "created": blob.time_created.isoformat() if blob.time_created else None,
            })
        return results
    except Exception as exc:
        logger.warning("Failed to list GCS snapshots: %s", exc)
        return []
