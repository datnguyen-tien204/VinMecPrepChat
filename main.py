"""
app/main.py – VinmecPrep AI  |  FastAPI production server (Day 12 edition)

Toàn bộ Day-12 optimizations áp dụng lên VinMec backend:

  ✅ Config từ environment (12-factor, app/config.py dataclass)
  ✅ Structured JSON logging (mọi request đều ra JSON)
  ✅ Public API key cho chat endpoints (X-API-Key) + Trainer key cho ops
  ✅ Rate limiting async Redis – phân tán theo user/IP, fail-closed
  ✅ Cost guard – Redis-backed budget theo tháng, shared giữa replicas
  ✅ Input validation – Pydantic v2, max_length, pattern
  ✅ /health (liveness) + /ready (readiness) + /metrics (ops)
  ✅ Graceful shutdown – SIGTERM drain 30s
  ✅ Security headers + X-Request-ID traceability
  ✅ CORS
  ✅ Async Kafka publish + async Redis poll (không block event loop)
  ✅ Timezone-aware datetime (UTC)
  ✅ Sentry optional (SENTRY_DSN)
  ✅ Embedding warmup trong lifespan
  ✅ Global exception handler → 500 JSON không leak stack trace

Scale strategy:
  API layer     : uvicorn --workers 4  (stateless, scale ngang)
  Async queue   : Kafka 5 partitions   (buffer burst traffic)
  Worker layer  : 5 consumer replicas × 10 concurrent jobs = 50 concurrent LLM calls
  Session cache : Redis (shared giữa mọi API instance)
  Rate limit    : Redis (distributed, không per-process)
"""
from app.main import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
