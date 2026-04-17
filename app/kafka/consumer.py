"""
app/kafka/consumer.py – Kafka consumer worker cho VinmecPrep AI.

Architecture (10k users):
  API server  →  Kafka vinmec.chat.jobs (5 partitions)
                     ↓  (partition key = session_id)
  5 Consumer instances (1 per partition, docker-compose replicas: 5)
                     ↓
  Process job  →  Redis key vinmec:result:{job_id}  (TTL 60s)
                     ↓
  API server polls Redis → trả về kết quả cho client

Concurrency model:
  - Mỗi consumer instance xử lý 1 partition (5 replicas × 1 partition = 5 parallel streams)
  - Bên trong mỗi consumer: CONCURRENT_JOBS task chạy song song với asyncio semaphore
  - chat() là blocking (LangGraph/LLM) → chạy trong ThreadPoolExecutor

Capacity estimation:
  - avg latency chat() ≈ 3–5s
  - CONCURRENT_JOBS = 10 per consumer
  - 5 consumers × 10 = 50 concurrent jobs
  - Throughput ≈ 50 / 4s ≈ 12–15 RPS → ~720 RPM → đủ cho spike 10k users
    (hầu hết user không chat cùng lúc, Kafka buffer hấp thụ burst)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import redis.asyncio as aioredis
from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaConnectionError

from app.core.config import REDIS_URL

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("vinmec.kafka.worker")

# ── Kafka config ──────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP    = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_JOBS         = os.getenv("KAFKA_TOPIC_JOBS",    "vinmec.chat.jobs")
TOPIC_RESULTS      = os.getenv("KAFKA_TOPIC_RESULTS", "vinmec.chat.results")
GROUP_ID           = "vinmec-workers"
CONSUMER_NAME      = f"worker-{uuid.uuid4().hex[:8]}"

# ── Concurrency ───────────────────────────────────────────────────────────────
CONCURRENT_JOBS    = int(os.getenv("WORKER_CONCURRENCY", "10"))

# ── Redis result TTL ──────────────────────────────────────────────────────────
RESULT_TTL_SECONDS = 60   # Client poll tối đa 60s


# ── Job processor ─────────────────────────────────────────────────────────────

def _sync_process_job(user_msg: str, history: list[dict]) -> dict:
    """Blocking call – chạy trong ThreadPoolExecutor."""
    from app.agent.vinmec_agent import chat
    return chat(user_msg, history)


async def _process_and_store(
    r:          aioredis.Redis,
    executor:   ThreadPoolExecutor,
    job_id:     str,
    session_id: str,
    user_msg:   str,
    history:    list[dict],
    partition:  int,
    offset:     int,
) -> None:
    """Xử lý một job và lưu kết quả vào Redis."""
    start = time.monotonic()
    logger.info(
        "[%s] START job_id=%s session=%s partition=%d offset=%d",
        CONSUMER_NAME, job_id, session_id, partition, offset,
    )

    result_key = f"vinmec:result:{job_id}"

    try:
        loop   = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, _sync_process_job, user_msg, history)

        payload = {
            "job_id":       job_id,
            "session_id":   session_id,
            "reply":        result["reply"],
            "blocked":      str(result["blocked"]).lower(),
            "guard_result": result.get("guard_result", ""),
            "ok":           "1",
        }

    except Exception as exc:
        logger.error("[%s] Job %s failed: %s", CONSUMER_NAME, job_id, exc, exc_info=True)
        payload = {
            "job_id":     job_id,
            "session_id": session_id,
            "reply":      "Đã xảy ra lỗi. Vui lòng thử lại hoặc gọi 1900 54 61 54.",
            "blocked":    "false",
            "ok":         "0",
            "error":      str(exc),
        }

    # Lưu vào Redis để API server poll
    await r.setex(result_key, RESULT_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))

    elapsed = time.monotonic() - start
    logger.info(
        "[%s] DONE job_id=%s elapsed=%.2fs partition=%d",
        CONSUMER_NAME, job_id, elapsed, partition,
    )


# ── Main consumer loop ────────────────────────────────────────────────────────

async def run_consumer():
    """
    Main consumer loop.
    Mỗi docker replica sẽ được Kafka assign 1 partition (với 5 replicas và 5 partitions).
    """
    r        = aioredis.from_url(REDIS_URL, decode_responses=True)
    executor = ThreadPoolExecutor(
        max_workers  = CONCURRENT_JOBS,
        thread_name_prefix = f"vinmec-job-{CONSUMER_NAME}",
    )
    semaphore = asyncio.Semaphore(CONCURRENT_JOBS)
    shutdown  = asyncio.Event()

    # Graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown.set)

    consumer = AIOKafkaConsumer(
        TOPIC_JOBS,
        bootstrap_servers    = KAFKA_BOOTSTRAP,
        group_id             = GROUP_ID,
        client_id            = CONSUMER_NAME,
        value_deserializer   = lambda v: json.loads(v.decode("utf-8")),
        key_deserializer     = lambda k: k.decode("utf-8") if k else None,
        # Bắt đầu từ earliest nếu chưa có committed offset
        auto_offset_reset    = "earliest",
        # Tắt auto-commit, commit thủ công sau khi xử lý xong
        enable_auto_commit   = False,
        # Fetch tối đa 10 messages mỗi poll → ghép với semaphore
        max_poll_records     = CONCURRENT_JOBS,
        # Tăng session timeout cho long-running jobs (chat ≈ 5s)
        session_timeout_ms   = 30_000,
        heartbeat_interval_ms= 3_000,
        # max_poll_interval phải > thời gian xử lý batch tối đa
        max_poll_interval_ms = CONCURRENT_JOBS * 10_000,  # 10s × 10 = 100s
    )

    await consumer.start()
    assigned = consumer.assignment()
    logger.info(
        "Consumer %s started. Group=%s Topic=%s Assigned partitions=%s",
        CONSUMER_NAME, GROUP_ID, TOPIC_JOBS,
        [tp.partition for tp in (assigned or [])],
    )

    active_tasks: set[asyncio.Task] = set()

    async def _bounded_process(msg):
        """Wrapper để giới hạn concurrent jobs bằng semaphore."""
        async with semaphore:
            data       = msg.value
            job_id     = data.get("job_id", str(uuid.uuid4()))
            session_id = data.get("session_id", "unknown")
            user_msg   = data.get("message", "")
            history_raw= data.get("history", "[]")

            try:
                history = json.loads(history_raw) if isinstance(history_raw, str) else history_raw
            except (json.JSONDecodeError, TypeError):
                history = []

            await _process_and_store(
                r         = r,
                executor  = executor,
                job_id    = job_id,
                session_id= session_id,
                user_msg  = user_msg,
                history   = history,
                partition = msg.partition,
                offset    = msg.offset,
            )

            # Commit offset sau khi xử lý thành công
            tp = TopicPartition(msg.topic, msg.partition)
            await consumer.commit({tp: msg.offset + 1})

    try:
        while not shutdown.is_set():
            try:
                # Lấy batch messages (non-blocking nếu empty)
                batch = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=2_000, max_records=CONCURRENT_JOBS),
                    timeout=3.0,
                )

                for _tp, messages in batch.items():
                    for msg in messages:
                        # Spawn task, track để cleanup
                        task = asyncio.create_task(_bounded_process(msg))
                        active_tasks.add(task)
                        task.add_done_callback(active_tasks.discard)

            except asyncio.TimeoutError:
                # Không có message mới, tiếp tục
                continue
            except KafkaConnectionError as e:
                logger.error("Kafka connection error: %s. Retry in 5s...", e)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error("Consumer poll error: %s", e, exc_info=True)
                await asyncio.sleep(1)

    finally:
        # Chờ các task đang chạy kết thúc (tối đa 30s)
        if active_tasks:
            logger.info("Chờ %d task đang chạy kết thúc...", len(active_tasks))
            await asyncio.wait(active_tasks, timeout=30.0)

        await consumer.stop()
        executor.shutdown(wait=True)
        await r.aclose()
        logger.info("Consumer %s shutdown hoàn tất", CONSUMER_NAME)


if __name__ == "__main__":
    asyncio.run(run_consumer())
