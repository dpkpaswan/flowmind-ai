# ── FlowMind AI -- Production Dockerfile ────────────────────────────────────
# Multi-stage build optimised for Cloud Run deployment.
# Uses non-root user for security, pip cache disabled for smaller image.
# 
# Build:   docker build -t flowmind-ai .
# Run:     docker run -p 8080:8080 --env-file .env flowmind-ai
# Deploy:  gcloud run deploy flowmind-ai --source .

FROM python:3.11-slim AS base

# ── Security: Create non-root user ──────────────────────────────────────────
RUN groupadd -r flowmind && useradd -r -g flowmind -d /app -s /sbin/nologin flowmind

WORKDIR /app

# ── Install dependencies (cached layer) ────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application code ──────────────────────────────────────────────────
COPY . .

# ── Security: Set ownership and switch to non-root ──────────────────────────
RUN chown -R flowmind:flowmind /app
USER flowmind

# ── Cloud Run uses PORT env variable (default 8080) ────────────────────────
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# ── Health check for container orchestrators ────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# ── Run with uvicorn (production settings) ──────────────────────────────────
# --workers 1 because Cloud Run handles horizontal scaling
# --timeout-keep-alive 70 for Cloud Run's 60s timeout
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--timeout-keep-alive", "70"]
