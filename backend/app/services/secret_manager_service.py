"""FlowMind AI -- Google Cloud Secret Manager Integration.

Loads sensitive configuration values from Google Cloud Secret Manager
at startup, falling back to environment variables / ``.env`` for local
development.

Secrets managed:
    * ``flowmind-firebase-url`` -- Firebase Realtime Database URL
    * ``flowmind-maps-api-key`` -- Google Maps API key
    * ``flowmind-gemini-config`` -- Gemini model configuration

Security model:
    * Secrets are fetched once at startup and cached in-process.
    * The Cloud Run service account needs ``secretmanager.secretAccessor``
      IAM role on the relevant secrets.
    * No secrets are stored on disk or logged.
"""

import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger("flowmind.secrets")

__all__ = [
    "get_secret",
    "load_secrets_into_config",
]

# ── Secret Manager Client (lazy) ────────────────────────────────────────────

_sm_client: Optional[Any] = None
_sm_available: Optional[bool] = None


def _get_client() -> Optional[Any]:
    """Lazy-initialise the Secret Manager client.

    Returns:
        A ``secretmanager_v1.SecretManagerServiceClient``, or ``None``.
    """
    global _sm_client, _sm_available

    if _sm_available is False:
        return None
    if _sm_client is not None:
        return _sm_client

    try:
        from google.cloud import secretmanager_v1

        _sm_client = secretmanager_v1.SecretManagerServiceClient()
        _sm_available = True
        logger.info("Secret Manager client initialised.")
        return _sm_client
    except Exception as exc:
        _sm_available = False
        logger.info(
            "Secret Manager unavailable (%s) -> using env vars.",
            type(exc).__name__,
        )
        return None


# ── Public API ──────────────────────────────────────────────────────────────


@lru_cache(maxsize=32)
def get_secret(secret_id: str, version: str = "latest") -> Optional[str]:
    """Fetch a secret value from Google Cloud Secret Manager.

    Results are cached in-process (via ``@lru_cache``) so repeated calls
    for the same secret don't hit the network.

    Args:
        secret_id: The secret name (e.g. ``"flowmind-firebase-url"``).
        version: Secret version (default ``"latest"``).

    Returns:
        The secret payload as a UTF-8 string, or ``None`` if the secret
        cannot be accessed.

    Complexity:
        Time:  O(1) on cache hit; O(network) on cache miss.
        Space: O(1) per cached secret.
    """
    client = _get_client()
    project = settings.GOOGLE_CLOUD_PROJECT

    if client is None or not project:
        return None

    try:
        name = f"projects/{project}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        payload: str = response.payload.data.decode("utf-8")
        logger.info("Loaded secret '%s' from Secret Manager.", secret_id)
        return payload
    except Exception as exc:
        logger.debug("Secret '%s' not accessible: %s", secret_id, exc)
        return None


def load_secrets_into_config() -> Dict[str, bool]:
    """Load secrets from Secret Manager and override config settings.

    Called once at startup.  Each secret is mapped to a specific
    ``Settings`` attribute.  If the secret is not available, the
    existing env-var value is preserved.

    Returns:
        A dict mapping secret names to ``True`` (loaded from SM) or
        ``False`` (using env var fallback).

    Secret-to-config mapping:
        * ``flowmind-firebase-url`` -> ``FIREBASE_DATABASE_URL``
        * ``flowmind-maps-api-key`` -> ``GOOGLE_MAPS_API_KEY``
    """
    results: Dict[str, bool] = {}

    _SECRET_MAP: Dict[str, str] = {
        "flowmind-firebase-url": "FIREBASE_DATABASE_URL",
        "flowmind-maps-api-key": "GOOGLE_MAPS_API_KEY",
    }

    for secret_id, config_attr in _SECRET_MAP.items():
        value = get_secret(secret_id)
        if value is not None:
            # Override the settings attribute dynamically
            setattr(settings, config_attr, value)
            results[secret_id] = True
            logger.info("Config '%s' loaded from Secret Manager.", config_attr)
        else:
            results[secret_id] = False
            logger.debug("Config '%s' using env var fallback.", config_attr)

    return results
