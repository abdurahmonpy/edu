# ---------------------------------------------------------------------------
# Englify — single container serving both the FastAPI backend and the static
# HTML frontend.  Optimised for Railway (build context = repository root).
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- system deps (curl is used by the healthcheck) -------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# --- python deps first, so code changes reuse the cached layer -------------
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# --- application code (includes the HTML frontend at the repo root) --------
COPY . .

# Railway injects $PORT; default is for local `docker run`.
ENV PORT=8000 \
    ENVIRONMENT=production \
    SERVE_FRONTEND=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health/ready" || exit 1

CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips '*'"]
