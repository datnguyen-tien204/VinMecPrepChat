from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from redis.asyncio import Redis

from app.core.config import settings

_BUDGET_NAMESPACE = "vinmec:budget"
GLOBAL_COST_SCOPE = "global"

_BUDGET_INCREMENT_LUA = """
local key = KEYS[1]
local increment = tonumber(ARGV[1])
local budget_limit = tonumber(ARGV[2])
local ttl_seconds = tonumber(ARGV[3])
local current = tonumber(redis.call('GET', key) or '0')
local next_total = current + increment

if next_total > budget_limit then
  return {0, current}
end

redis.call('SET', key, tostring(next_total), 'EX', ttl_seconds)
return {1, next_total}
"""


def current_budget_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def seconds_until_next_month() -> int:
    now = datetime.now(timezone.utc)
    next_month = (now.replace(day=28) + timedelta(days=4)).replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return max(int((next_month - now).total_seconds()), 1)


def budget_key(scope: str) -> str:
    return f"{_BUDGET_NAMESPACE}:{current_budget_period()}:{scope}"


async def get_monthly_cost(redis: Redis, scope: str) -> float:
    raw = await redis.get(budget_key(scope))
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0


async def check_and_record_cost(redis: Redis, scope: str, input_tokens: int, output_tokens: int) -> float:
    increment = (
        (input_tokens / 1_000_000) * settings.price_input_per_1m_tokens_usd
        + (output_tokens / 1_000_000) * settings.price_output_per_1m_tokens_usd
    )
    if increment <= 0:
        return await get_monthly_cost(redis, scope)

    ttl = seconds_until_next_month()
    try:
        allowed, total = await redis.eval(
            _BUDGET_INCREMENT_LUA,
            1,
            budget_key(scope),
            increment,
            settings.monthly_budget_usd,
            ttl,
        )
    except Exception as exc:
        raise HTTPException(503, "Cost guard tạm thời không khả dụng.") from exc

    if int(allowed) != 1:
        raise HTTPException(402, "Đã vượt ngân sách tháng cho client này.")

    await redis.incrbyfloat(budget_key(GLOBAL_COST_SCOPE), increment)
    await redis.expire(budget_key(GLOBAL_COST_SCOPE), ttl)
    return float(total)
