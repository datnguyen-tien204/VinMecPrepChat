from __future__ import annotations

from fastapi import HTTPException
from redis.asyncio import Redis

from app.core.config import settings

_RATE_LIMIT_NAMESPACE = "vinmec:rate-limit"
_SESSION_OWNER_NAMESPACE = "vinmec:session-owner"


def _rate_limit_key(subject: str) -> str:
    return f"{_RATE_LIMIT_NAMESPACE}:{subject}"


def _session_owner_key(session_id: str) -> str:
    return f"{_SESSION_OWNER_NAMESPACE}:{session_id}"


async def ensure_session_owner(redis: Redis, session_id: str, principal: str) -> None:
    owner_key = _session_owner_key(session_id)
    ttl = max(settings.redis_session_ttl, 300)
    created = await redis.set(owner_key, principal, ex=ttl, nx=True)
    if created:
        return

    owner = await redis.get(owner_key)
    if owner != principal:
        raise HTTPException(403, "Session này thuộc về một client khác.")
    await redis.expire(owner_key, ttl)


async def _consume_rate_limit(redis: Redis, subject: str, scope_name: str) -> None:
    key = _rate_limit_key(subject)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > settings.rate_limit_rpm:
        raise HTTPException(
            status_code=429,
            detail=f"Quá {settings.rate_limit_rpm} requests/phút ở mức {scope_name}. Vui lòng thử lại sau.",
            headers={"Retry-After": "60"},
        )


async def enforce_rate_limit(redis: Redis, client_scope: str, session_scope: str | None = None) -> None:
    try:
        await _consume_rate_limit(redis, client_scope, "client")
        if session_scope:
            await _consume_rate_limit(redis, session_scope, "session")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Rate limiter tạm thời không khả dụng.") from exc
