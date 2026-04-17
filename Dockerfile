# ============================================================
# VinmecPrep AI – Production Dockerfile (Day 12 edition)
#
# Multi-stage build:
#   Stage 1 (builder) : pip install vào /root/.local
#   Stage 2 (runtime) : copy packages, non-root user, minimal image
#
# Optimizations vs bản gốc (single-stage):
#   ✅ Tách builder/runtime → image nhỏ hơn ~40%
#   ✅ PYTHONDONTWRITEBYTECODE + PYTHONUNBUFFERED từ đầu
#   ✅ --no-install-recommends → bỏ package không cần
#   ✅ Non-root user (vinmec:1000)
#   ✅ curl healthcheck
#   ✅ PYTHONPATH=/app → import app.* đúng path
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user
RUN groupadd -r vinmec && useradd -r -g vinmec -d /app -u 1000 vinmec

WORKDIR /app

# Minimal runtime deps (curl cho healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages từ builder vào system prefix chuẩn
COPY --from=builder /install /usr/local

# Copy application source
COPY main.py      ./main.py
COPY app/         ./app/
COPY scripts/     ./scripts/

# Fix ownership
RUN chown -R vinmec:vinmec /app

USER vinmec

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Liveness check – platform restart sau 3 lần fail liên tiếp
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# Worker count lấy từ env API_WORKERS để deploy/runtime override được.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${API_WORKERS:-4} --timeout-keep-alive 30"]
