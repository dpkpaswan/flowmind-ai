"""FlowMind AI -- Application Configuration.

Loads settings from environment variables (or ``.env`` file) with
sensible defaults for local development.  Uses ``pydantic-settings``
for type-safe parsing and validation.

All GCP service integrations fall back gracefully when their respective
environment variables are not set.  The ``Settings.Config`` inner class
uses ``extra = "ignore"`` to silently skip unknown env vars, making
deployment across different environments seamless.

Security note:
    Sensitive values (API keys, database URLs) should be loaded from
    Google Cloud Secret Manager in production via
    ``secret_manager_service.load_secrets_into_config()``.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings

__all__ = ["settings", "Settings"]


class Settings(BaseSettings):
    """Application settings loaded from ``.env`` or environment variables.

    Attributes:
        APP_NAME: Display name shown in API docs and health check.
        APP_VERSION: Semantic version string (SemVer 2.0).
        DEBUG: Enable debug-level logging and auto-reload.
        CORS_ORIGINS: Comma-separated list of allowed CORS origins.
        GEMINI_MODEL: Vertex AI model identifier for AI assistant.
        VERTEX_AI_LOCATION: GCP region for Vertex AI requests.
        FIREBASE_DATABASE_URL: Firebase RTDB URL (empty = use mock).
        GOOGLE_CLOUD_PROJECT: GCP project ID for all Google services.
        BIGQUERY_DATASET: BigQuery dataset for crowd analytics.
        GOOGLE_MAPS_API_KEY: Frontend-only; stored here for reference.
        STADIUM_NAME: Display name of the stadium.
        STADIUM_CAPACITY: Maximum stadium capacity (seats).
        MOCK_UPDATE_INTERVAL: Seconds between background data refreshes.
        DENSITY_WARNING_THRESHOLD: Zone density threshold for warnings.
        DENSITY_CRITICAL_THRESHOLD: Zone density threshold for critical.
        WAIT_WARNING_MINUTES: Facility wait threshold for info alerts.
        WAIT_CRITICAL_MINUTES: Facility wait threshold for critical alerts.
        RATE_LIMIT_PER_MINUTE: Global API rate limit per IP address.
        RATE_LIMIT_CHAT_PER_MINUTE: Chat endpoint rate limit per IP.
        SNAPSHOT_CACHE_TTL: Seconds to cache generated snapshots.
        MAX_CHAT_MESSAGE_LENGTH: Maximum length of chat messages.
    """

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "FlowMind AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── CORS ─────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Gemini AI (Vertex AI SDK) ─────────────────────────
    GEMINI_MODEL: str = "gemini-2.5-flash"
    VERTEX_AI_LOCATION: str = "us-central1"

    # ── Firebase Realtime Database ────────────────────────
    FIREBASE_DATABASE_URL: str = ""

    # ── Google Cloud ──────────────────────────────────────
    GOOGLE_CLOUD_PROJECT: str = ""

    # ── BigQuery Analytics ────────────────────────────────
    BIGQUERY_DATASET: str = "flowmind_analytics"

    # ── Google Maps (frontend reference) ──────────────────
    GOOGLE_MAPS_API_KEY: str = ""

    # ── Stadium Config ───────────────────────────────────
    STADIUM_NAME: str = "MetaStadium Arena"
    STADIUM_CAPACITY: int = 60000
    MOCK_UPDATE_INTERVAL: int = 30  # seconds between mock data updates

    # ── Alert Thresholds ─────────────────────────────────
    # These thresholds are referenced by alert_service.py and helpers.py
    DENSITY_WARNING_THRESHOLD: float = 0.75   # 75% capacity
    DENSITY_CRITICAL_THRESHOLD: float = 0.90  # 90% capacity
    WAIT_WARNING_MINUTES: int = 10            # 10-min wait -> info alert
    WAIT_CRITICAL_MINUTES: int = 20           # 20-min wait -> critical alert

    # ── Performance Tuning ───────────────────────────────
    SNAPSHOT_CACHE_TTL: int = 10              # seconds to cache snapshots
    GZIP_MINIMUM_SIZE: int = 500             # bytes before GZip kicks in

    # ── Security ─────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 100         # global API rate limit per IP
    RATE_LIMIT_CHAT_PER_MINUTE: int = 20     # chat endpoint rate limit per IP
    MAX_CHAT_MESSAGE_LENGTH: int = 500       # max chars in chat messages

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse the comma-separated CORS_ORIGINS into a list of strings.

        Returns:
            A list of origin URLs, whitespace-trimmed.
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # silently ignore unknown env vars


# Singleton settings instance -- imported across the application
settings: Settings = Settings()
