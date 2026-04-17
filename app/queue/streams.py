"""
app/queue/streams.py – Redis Stream consumer worker cho VinmecPrep AI.

Architecture:
  API server  →  XADD vinmec:jobs  →  Stream
  Worker(s)   →  XREADGROUP         →  Process → XADD vinmec:results

Dùng cho long-running requests (> 30s) hoặc batch jobs như ingest.
Với 10k users, 4 worker replicas trong docker-compose là đủ cho ~200 concurrent.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time
import uuid

import redis.asyncio as aioredis

from app.core.config import REDIS_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("vinmec.worker")

# ── Stream / Group config ─────────────────────────────────────────────────────
STREAM_JOBS    = "vinmec:jobs"
STREAM_RESULTS = "vinmec:results"
GROUP_NAME     = "vinmec-workers"
CONSUMER_NAME  = f"worker-{uuid.uuid4().hex[:8]}"
BLOCK_MS       = 2_000   # poll mỗi 2 giây
MAX_LEN        = 10_000  # giới hạn stream length


async def _ensure_group(r: aioredis.Redis):
    """Tạo consumer group nếu chưa có."""
    try:
        await r.xgroup_create(STREAM_JOBS, GROUP_NAME, id="0", mkstream=True)
        logger.info("Consumer group '%s' created on stream '%s'", GROUP_NAME, STREAM_JOBS)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.debug("Consumer group already exists: %s", GROUP_NAME)
        else:
            raise


async def _process_job(r: aioredis.Redis, job_id: str, data: dict):
    """
    Xử lý một chat job từ stream.
    """
    start = time.monotonic()
    session_id  = data.get("session_id", "")
    user_msg    = data.get("message", "")
    history_raw = data.get("history", "[]")

    try:
        history = json.loads(history_raw) if isinstance(history_raw, str) else history_raw
    except json.JSONDecodeError:
        history = []

    logger.info("[%s] Processing job: session=%s msg=%.60s...", CONSUMER_NAME, session_id, user_msg)

    result_payload: dict
    try:
        # Import lazily để không block startup
        from app.agent.vinmec_agent import chat
        result = chat(user_msg, history)
        result_payload = {
            "session_id":   session_id,
            "reply":        result["reply"],
            "blocked":      str(result["blocked"]),
            "guard_result": result["guard_result"],
            "ok":           "1",
        }
    except Exception as exc:
        logger.error("[%s] Job %s failed: %s", CONSUMER_NAME, job_id, exc, exc_info=True)
        result_payload = {
            "session_id": session_id,
            "reply":      "Đã xảy ra lỗi. Vui lòng thử lại hoặc gọi 1900 54 61 54.",
            "blocked":    "false",
            "ok":         "0",
            "error":      str(exc),
        }

    # Publish result
    result_key = f"vinmec:result:{session_id}:{job_id}"
    await r.setex(result_key, 60, json.dumps(result_payload))

    # ACK + push to results stream
    await r.xack(STREAM_JOBS, GROUP_NAME, job_id)
    await r.xadd(STREAM_RESULTS, result_payload, maxlen=MAX_LEN)

    elapsed = time.monotonic() - start
    logger.info("[%s] Job %s done in %.2fs", CONSUMER_NAME, job_id, elapsed)


async def run_worker():
    """Main worker loop."""
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    await _ensure_group(r)

    logger.info("Worker %s started. Listening on stream: %s", CONSUMER_NAME, STREAM_JOBS)

    # Graceful shutdown
    shutdown = asyncio.Event()

    def _handle_signal(*_):
        logger.info("Shutdown signal received")
        shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    # First: reclaim any pending messages from crashed workers
    pending = await r.xpending_range(STREAM_JOBS, GROUP_NAME, "-", "+", count=10)
    if pending:
        logger.info("Reclaiming %d pending messages", len(pending))
        for entry in pending:
            msg_id = entry["message_id"]
            claimed = await r.xclaim(STREAM_JOBS, GROUP_NAME, CONSUMER_NAME, 30_000, [msg_id])
            for cid, cdata in claimed:
                await _process_job(r, cid, cdata)

    # Main loop
    while not shutdown.is_set():
        try:
            messages = await r.xreadgroup(
                GROUP_NAME, CONSUMER_NAME,
                {STREAM_JOBS: ">"},
                count=1,
                block=BLOCK_MS,
            )
            if not messages:
                continue
            for stream_name, entries in messages:
                for msg_id, data in entries:
                    await _process_job(r, msg_id, data)
        except aioredis.ConnectionError as e:
            logger.error("Redis connection error: %s. Retrying in 5s...", e)
            await asyncio.sleep(5)
        except Exception as e:
            logger.error("Worker error: %s", e, exc_info=True)
            await asyncio.sleep(1)

    await r.aclose()
    logger.info("Worker %s shut down cleanly", CONSUMER_NAME)


if __name__ == "__main__":
    asyncio.run(run_worker())
