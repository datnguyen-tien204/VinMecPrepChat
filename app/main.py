from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.auth import require_client_key, require_trainer_key, resolve_request_scopes
from app.core.config import settings
from app.core.cost_guard import GLOBAL_COST_SCOPE, check_and_record_cost, get_monthly_cost
from app.core.rate_limiter import enforce_rate_limit, ensure_session_owner
from app.kafka.producer import kafka_producer

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
        logger.info(json.dumps({"event": "sentry_init", "ok": True}))
    except ImportError:
        logger.warning(json.dumps({"event": "sentry_skip", "reason": "sentry-sdk not installed"}))

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0
_redis: Optional[aioredis.Redis] = None

POLL_INTERVAL_S = 0.25


def _safe_redis_target() -> str:
    target = settings.redis_url.rsplit("@", 1)[-1]
    return target.removeprefix("redis://")


async def _get_redis() -> aioredis.Redis:
    if not _redis:
        raise HTTPException(503, "Redis chưa sẵn sàng.")
    return _redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _is_ready

    logger.info(
        json.dumps(
            {
                "event": "startup",
                "app": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "kafka": settings.kafka_bootstrap,
            }
        )
    )

    _redis = aioredis.from_url(settings.redis_url, decode_responses=True, max_connections=50)
    try:
        await _redis.ping()
        logger.info(json.dumps({"event": "redis_ok", "target": _safe_redis_target()}))
    except Exception as exc:
        logger.error(json.dumps({"event": "redis_fail", "error": str(exc)}))
        raise

    await kafka_producer.start()

    if settings.embedding_warmup:
        await asyncio.sleep(0)
        try:
            from app.rag.weaviate_client import VECTORIZER

            if VECTORIZER == "none":
                from app.rag.embedder import warmup_embedding_backend

                info = warmup_embedding_backend()
                logger.info(json.dumps({"event": "embedding_warmup_ok", **info}))
        except Exception as exc:
            logger.warning(json.dumps({"event": "embedding_warmup_skip", "error": str(exc)}))

    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    await kafka_producer.stop()
    if _redis:
        await _redis.aclose()
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI trợ lý chuẩn bị khám Vinmec – production edition (Day 12)",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Trainer-Key", "X-User-ID"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    global _request_count, _error_count

    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start = time.time()
    _request_count += 1

    try:
        response: Response = await call_next(request)
    except Exception:
        _error_count += 1
        raise

    duration_ms = round((time.time() - start) * 1000, 1)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Request-ID"] = request_id
    if "server" in response.headers:
        del response.headers["server"]

    logger.info(
        json.dumps(
            {
                "event": "http",
                "rid": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": duration_ms,
                "ip": request.client.host if request.client else "",
            }
        )
    )
    return response


async def _get_history(redis: aioredis.Redis, session_id: str) -> list[dict]:
    try:
        raw = await redis.get(f"session:{session_id}")
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def _save_history(redis: aioredis.Redis, session_id: str, history: list[dict]):
    try:
        await redis.setex(
            f"session:{session_id}",
            settings.redis_session_ttl,
            json.dumps(history[-40:]),
        )
    except Exception as exc:
        logger.warning(json.dumps({"event": "session_save_fail", "error": str(exc)}))


async def _poll_result(redis: aioredis.Redis, job_id: str, timeout_s: float) -> dict | None:
    result_key = f"vinmec:result:{job_id}"
    deadline = asyncio.get_running_loop().time() + timeout_s

    while asyncio.get_running_loop().time() < deadline:
        try:
            raw = await redis.get(result_key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning(json.dumps({"event": "redis_poll_error", "error": str(exc)}))

        await asyncio.sleep(POLL_INTERVAL_S)

    return None


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    history: list[Message] = Field(default_factory=list, max_length=40)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    job_id: str
    blocked: bool
    guard_result: str
    request_id: str
    timestamp: str


class ChatJobSubmitted(BaseModel):
    job_id: str
    session_id: str
    status: str = "queued"


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    rating: str = Field(..., pattern="^(like|dislike)$")
    comment: Optional[str] = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    uuid: str
    session_id: str
    rating: str
    saved: bool


class FeedbackEndRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[list[str]] = Field(default=None, max_length=10)


class FeedbackEndResponse(BaseModel):
    uuid: str
    session_id: str
    rating: int
    saved: bool


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "chat": "POST /chat",
            "chat_async": "POST /chat/async → GET /chat/result/{job_id}",
            "feedback": "POST /feedback",
            "health": "GET /health",
            "ready": "GET /ready",
            "auth": "X-API-Key bắt buộc cho chat/feedback",
            "metrics": "GET /metrics (requires X-Trainer-Key)",
        },
    }


@app.get("/health", tags=["Operations"])
async def health():
    redis = _redis
    try:
        if redis:
            await redis.ping()
        redis_ok = bool(redis)
    except Exception:
        redis_ok = False

    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {
            "redis": "ok" if redis_ok else "error",
            "llm": settings.llm_model,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
async def ready():
    redis = await _get_redis()
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    try:
        await redis.ping()
    except Exception as exc:
        logger.warning(json.dumps({"event": "ready_check_fail", "error": str(exc)}))
        raise HTTPException(503, "Redis chưa sẵn sàng")
    try:
        await kafka_producer.check_health()
    except Exception as exc:
        logger.warning(json.dumps({"event": "ready_check_fail", "component": "kafka", "error": str(exc)}))
        raise HTTPException(503, "Kafka chưa sẵn sàng")
    return {"ready": True}


@app.get("/metrics", tags=["Operations"])
async def metrics(_key: str = Depends(require_trainer_key)):
    redis = await _get_redis()
    monthly_cost = await get_monthly_cost(redis, GLOBAL_COST_SCOPE)
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "monthly_cost_usd": round(monthly_cost, 6),
        "monthly_budget_usd": settings.monthly_budget_usd,
        "budget_used_pct": round(monthly_cost / max(settings.monthly_budget_usd, 0.0001) * 100, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    client_key: str = Depends(require_client_key),
):
    redis = await _get_redis()
    session_id = req.session_id or str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    rid = getattr(request.state, "request_id", "")
    scopes = resolve_request_scopes(request, client_key, session_id)
    client_scope = scopes["client_scope"]
    session_scope = scopes.get("session_scope")

    history = [m.model_dump() for m in req.history] if req.history else await _get_history(redis, session_id)

    await ensure_session_owner(redis, session_id, client_scope)
    await enforce_rate_limit(redis, client_scope, session_scope)
    input_tokens_est = len(req.message.split()) * 2 + len(history) * 10
    await check_and_record_cost(redis, client_scope, input_tokens_est, 0)

    logger.info(
        json.dumps(
            {
                "event": "chat_submit",
                "rid": rid,
                "session_id": session_id,
                "job_id": job_id,
                "msg_len": len(req.message),
            }
        )
    )

    try:
        await kafka_producer.send_job(
            job_id,
            session_id,
            {
                "message": req.message,
                "history": json.dumps(history, ensure_ascii=False),
            },
        )
    except Exception as exc:
        logger.error(json.dumps({"event": "kafka_send_fail", "error": str(exc), "rid": rid}))
        raise HTTPException(503, "Hàng đợi tạm thời không khả dụng.")

    result = await _poll_result(redis, job_id, timeout_s=settings.chat_poll_timeout)
    if result is None:
        raise HTTPException(504, "Yêu cầu đang được xử lý, vui lòng thử lại sau.")

    blocked = result.get("blocked", "false").lower() == "true"
    if not blocked:
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": result["reply"]})
        await _save_history(redis, session_id, history)

    output_tokens_est = len(result["reply"].split()) * 2
    await check_and_record_cost(redis, client_scope, 0, output_tokens_est)

    return ChatResponse(
        reply=result["reply"],
        session_id=session_id,
        job_id=job_id,
        blocked=blocked,
        guard_result=result.get("guard_result", ""),
        request_id=rid,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/chat/async", response_model=ChatJobSubmitted, tags=["Chat"])
async def chat_async_endpoint(
    req: ChatRequest,
    request: Request,
    client_key: str = Depends(require_client_key),
):
    redis = await _get_redis()
    session_id = req.session_id or str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    scopes = resolve_request_scopes(request, client_key, session_id)
    client_scope = scopes["client_scope"]
    session_scope = scopes.get("session_scope")
    history = [m.model_dump() for m in req.history] if req.history else await _get_history(redis, session_id)

    await ensure_session_owner(redis, session_id, client_scope)
    await enforce_rate_limit(redis, client_scope, session_scope)
    input_tokens_est = len(req.message.split()) * 2 + len(history) * 10
    await check_and_record_cost(redis, client_scope, input_tokens_est, 0)

    try:
        await kafka_producer.send_job(
            job_id,
            session_id,
            {
                "message": req.message,
                "history": json.dumps(history, ensure_ascii=False),
            },
        )
    except Exception as exc:
        logger.error(json.dumps({"event": "kafka_send_fail", "error": str(exc)}))
        raise HTTPException(503, "Hàng đợi tạm thời không khả dụng.")

    return ChatJobSubmitted(job_id=job_id, session_id=session_id)


@app.get("/chat/result/{job_id}", tags=["Chat"])
async def get_chat_result(
    job_id: str,
    request: Request,
    client_key: str = Depends(require_client_key),
):
    redis = await _get_redis()
    client_scope = resolve_request_scopes(request, client_key)["client_scope"]
    await enforce_rate_limit(redis, client_scope)

    try:
        raw = await redis.get(f"vinmec:result:{job_id}")
    except Exception:
        raw = None

    if not raw:
        return JSONResponse(status_code=202, content={"status": "processing", "job_id": job_id})

    result = json.loads(raw)
    blocked = result.get("blocked", "false").lower() == "true"
    session_id = result.get("session_id")
    if session_id:
        await ensure_session_owner(redis, session_id, client_scope)

    return {
        "status": "done",
        "job_id": job_id,
        "session_id": session_id,
        "reply": result.get("reply"),
        "blocked": blocked,
        "guard_result": result.get("guard_result", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/", response_model=ChatResponse, tags=["Chat"], include_in_schema=False)
async def chat_root(
    req: ChatRequest,
    request: Request,
    client_key: str = Depends(require_client_key),
):
    return await chat_endpoint(req, request, client_key)


@app.post("/feedback", response_model=FeedbackResponse, tags=["Feedback"])
async def feedback_endpoint(
    req: FeedbackRequest,
    request: Request,
    client_key: str = Depends(require_client_key),
):
    from app.db.feedback import save_feedback

    redis = await _get_redis()
    scopes = resolve_request_scopes(request, client_key, req.session_id)
    client_scope = scopes["client_scope"]
    session_scope = scopes.get("session_scope")
    await ensure_session_owner(redis, req.session_id, client_scope)
    await enforce_rate_limit(redis, client_scope, session_scope)

    messages = await _get_history(redis, req.session_id)
    if not messages:
        raise HTTPException(404, "Không tìm thấy lịch sử chat. Session có thể đã hết hạn.")

    loop = asyncio.get_running_loop()
    try:
        obj_uuid = await loop.run_in_executor(None, save_feedback, req.session_id, req.rating, messages, req.comment)
    except ValueError as exc:
        raise HTTPException(409, str(exc))

    return FeedbackResponse(uuid=obj_uuid, session_id=req.session_id, rating=req.rating, saved=True)


@app.post("/feedback/end", response_model=FeedbackEndResponse, tags=["Feedback"])
async def feedback_end_endpoint(
    req: FeedbackEndRequest,
    request: Request,
    client_key: str = Depends(require_client_key),
):
    from app.db.feedback import save_feedback_end

    redis = await _get_redis()
    scopes = resolve_request_scopes(request, client_key, req.session_id)
    client_scope = scopes["client_scope"]
    session_scope = scopes.get("session_scope")
    await ensure_session_owner(redis, req.session_id, client_scope)
    await enforce_rate_limit(redis, client_scope, session_scope)

    messages = await _get_history(redis, req.session_id)
    if not messages:
        raise HTTPException(404, "Không tìm thấy lịch sử chat. Session có thể đã hết hạn.")

    loop = asyncio.get_running_loop()
    try:
        obj_uuid = await loop.run_in_executor(
            None,
            save_feedback_end,
            req.session_id,
            req.rating,
            messages,
            req.comment,
            req.tags,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))

    return FeedbackEndResponse(uuid=obj_uuid, session_id=req.session_id, rating=req.rating, saved=True)


@app.get("/feedback", tags=["Trainer"], dependencies=[Depends(require_trainer_key)])
async def get_feedback_list(
    rating: Optional[str] = Query(default=None, pattern="^(like|dislike)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    from app.db.feedback import get_feedback

    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, get_feedback, rating, limit, offset)
    return {"total": len(rows), "offset": offset, "items": rows}


@app.get("/feedback/search", tags=["Trainer"], dependencies=[Depends(require_trainer_key)])
async def search_feedback_endpoint(
    q: str = Query(..., min_length=1, max_length=500),
    rating: Optional[str] = Query(default=None, pattern="^(like|dislike)$"),
    limit: int = Query(default=20, ge=1, le=100),
):
    from app.db.feedback import search_feedback

    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, search_feedback, q, rating, limit)
    return {"query": q, "rating": rating, "total": len(results), "items": results}


@app.get("/feedback/stats", tags=["Trainer"], dependencies=[Depends(require_trainer_key)])
async def get_feedback_stats():
    from app.db.feedback import count_feedback

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, count_feedback)


@app.get("/feedback/end", tags=["Trainer"], dependencies=[Depends(require_trainer_key)])
async def get_feedback_end_list(
    rating: Optional[int] = Query(default=None, ge=1, le=5),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    from app.db.feedback import get_feedback_end

    loop = asyncio.get_running_loop()
    rows = await loop.run_in_executor(None, get_feedback_end, rating, limit, offset)
    return {"total": len(rows), "offset": offset, "items": rows}


@app.get("/feedback/end/stats", tags=["Trainer"], dependencies=[Depends(require_trainer_key)])
async def get_feedback_end_stats():
    from app.db.feedback import count_feedback_end

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, count_feedback_end)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    global _error_count
    _error_count += 1
    logger.error(json.dumps({"event": "unhandled_error", "path": request.url.path, "error": str(exc)}), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Đã xảy ra lỗi. Vui lòng thử lại hoặc gọi 1900 54 61 54."},
    )


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    import uvicorn

    logger.info(
        json.dumps(
            {
                "event": "main_start",
                "host": settings.host,
                "port": settings.port,
                "workers": settings.api_workers,
            }
        )
    )
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.api_workers,
        reload=settings.debug,
        timeout_keep_alive=30,
        timeout_graceful_shutdown=30,
    )
