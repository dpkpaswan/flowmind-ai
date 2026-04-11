"""
FlowMind AI — Application Configuration
Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from .env file or environment."""

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "FlowMind AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── CORS ─────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Gemini AI ────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── Firebase Realtime Database ────────────────────────
    FIREBASE_DATABASE_URL: str = ""

    # ── Google Cloud ──────────────────────────────────────
    GOOGLE_CLOUD_PROJECT: str = ""

    # ── Google Maps (used by frontend, stored here for reference) ────────────
    GOOGLE_MAPS_API_KEY: str = ""

    # ── Stadium Config ───────────────────────────────────
    STADIUM_NAME: str = "MetaStadium Arena"
    STADIUM_CAPACITY: int = 60000
    MOCK_UPDATE_INTERVAL: int = 30  # seconds between mock data updates

    # ── Alert Thresholds ─────────────────────────────────
    DENSITY_WARNING_THRESHOLD: float = 0.75
    DENSITY_CRITICAL_THRESHOLD: float = 0.90
    WAIT_WARNING_MINUTES: int = 10
    WAIT_CRITICAL_MINUTES: int = 20

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # silently ignore unknown env vars (e.g. GOOGLE_MAPS_API_KEY)


# Singleton settings instance
settings = Settings()
