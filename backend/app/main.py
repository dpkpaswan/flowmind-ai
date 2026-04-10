"""
FlowMind AI — FastAPI Application Entry Point
Predictive crowd intelligence system for large sports stadiums.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.data.mock_generator import generate_snapshot
from app.routers import crowd, wait_times, alerts, chat, simulation, emergency


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
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
