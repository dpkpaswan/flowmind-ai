"""
FlowMind AI — FastAPI Application Entry Point
Predictive crowd intelligence system for large sports stadiums.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.mock_generator import generate_snapshot
from app.routers import crowd, wait_times, alerts, chat, simulation, emergency

logger = logging.getLogger("flowmind")


# ── Google Cloud Logging Setup ───────────────────────────────────────────────

def _setup_cloud_logging():
    """
    Attach Google Cloud Logging handler so structured logs appear in
    Cloud Logging on GCP.  Falls back to standard logging locally.
    """
    try:
        import google.cloud.logging as cloud_logging

        client = cloud_logging.Client(
            project=settings.GOOGLE_CLOUD_PROJECT or None,
        )
        client.setup_logging(log_level=logging.INFO)
        print("[LOG] Google Cloud Logging attached.")
    except Exception as exc:
        # Local / no credentials → standard stderr logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        )
        print(f"[LOG] Cloud Logging unavailable ({type(exc).__name__}) → using local logging.")


# ── Lifespan: Initialize mock data & start background refresh ────────────────

async def _background_data_refresh():
    """Periodically refresh mock stadium data to simulate real-time changes."""
    while True:
        try:
            generate_snapshot()
        except Exception:
            pass
        await asyncio.sleep(settings.MOCK_UPDATE_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Setup cloud logging first
    _setup_cloud_logging()

    # Startup: generate initial snapshot + start background task
    print(f"[STADIUM] {settings.APP_NAME} v{settings.APP_VERSION} starting up...")
    generate_snapshot()
    print("[DATA] Initial stadium data generated.")

    task = asyncio.create_task(_background_data_refresh())
    print(f"[REFRESH] Background data refresh every {settings.MOCK_UPDATE_INTERVAL}s.")
    print(f"[AI] Gemini model: {settings.GEMINI_MODEL}")
    print(f"[KEY] Gemini API key: {'configured' if settings.GEMINI_API_KEY else 'NOT SET - using fallback AI'}")
    print(f"[READY] Docs at http://localhost:8000/docs")

    yield

    # Shutdown
    task.cancel()
    print("[SHUTDOWN] FlowMind AI shutting down.")


# ── App Creation ─────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Predictive crowd intelligence system for large sports stadiums. "
        "Helps fans avoid crowds, reduce wait times, and navigate smarter using AI."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS Middleware ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Logging Middleware ───────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every API request with method, path, status, and duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "api_request",
        extra={
            "json_fields": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client": request.client.host if request.client else "unknown",
            }
        },
    )
    return response


# ── Register Routers ────────────────────────────────────────────────────────

app.include_router(crowd.router)
app.include_router(wait_times.router)
app.include_router(alerts.router)
app.include_router(chat.router)
app.include_router(simulation.router)
app.include_router(emergency.router)


# ── Root Endpoint ────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health check and API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "crowd": "/api/crowd/current",
            "predictions": "/api/crowd/predict",
            "heatmap": "/api/crowd/heatmap",
            "wait_times": "/api/wait-times",
            "alerts": "/api/alerts",
            "chat": "/api/chat",
            "simulation": "/api/simulation/status",
            "emergency": "/api/emergency/status",
        },
    }
