"""
app/kafka/producer.py – Async Kafka producer singleton cho VinmecPrep AI.

Dùng aiokafka để push chat jobs lên topic vinmec.chat.jobs với 5 partitions.
Partition key = session_id → đảm bảo ordering per user (cùng session → cùng partition).

Usage:
    await kafka_producer.start()          # trong lifespan FastAPI
    await kafka_producer.send_job(data)   # trong /chat endpoint
    await kafka_producer.stop()           # khi shutdown
"""
from __future__ import annotations

import inspect
import json
import logging
import os

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_JOBS      = os.getenv("KAFKA_TOPIC_JOBS",    "vinmec.chat.jobs")
TOPIC_RESULTS   = os.getenv("KAFKA_TOPIC_RESULTS", "vinmec.chat.results")
NUM_PARTITIONS  = 5


def _serialize(v: dict) -> bytes:
    return json.dumps(v, ensure_ascii=False).encode("utf-8")


def _serialize_key(k: str | None) -> bytes | None:
    return k.encode("utf-8") if k else None


class VinmecKafkaProducer:
    """Singleton wrapper cho AIOKafkaProducer."""

    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers    = KAFKA_BOOTSTRAP,
            value_serializer     = _serialize,
            key_serializer       = _serialize_key,
            # Đảm bảo không mất message
            acks                 = "all",
            # Tăng throughput: batch nhỏ, linger ngắn
            linger_ms            = 5,
            max_batch_size       = 16_384,
            # Backoff khi broker tạm thời unavailable
            retry_backoff_ms     = 200,
            # Idempotent producer – tránh duplicate khi retry
            enable_idempotence   = True,
        )
        await self._producer.start()
        logger.info("Kafka producer connected to %s", KAFKA_BOOTSTRAP)

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

    async def check_health(self) -> bool:
        if not self._producer:
            raise RuntimeError("Kafka producer chưa được khởi tạo.")

        producer = self._producer
        partitions_for = getattr(producer, "partitions_for", None)
        if callable(partitions_for):
            partitions = partitions_for(TOPIC_JOBS)
            if inspect.isawaitable(partitions):
                partitions = await partitions
            if not partitions:
                raise RuntimeError(f"Không đọc được metadata cho topic {TOPIC_JOBS}.")
            return True

        client = getattr(producer, "client", None)
        if client is not None:
            bootstrap = getattr(client, "bootstrap", None)
            if callable(bootstrap):
                result = bootstrap()
                if inspect.isawaitable(result):
                    await result
                return True

            force_metadata_update = getattr(client, "force_metadata_update", None)
            if callable(force_metadata_update):
                result = force_metadata_update()
                if inspect.isawaitable(result):
                    await result
                return True

        return True

    async def send_job(self, job_id: str, session_id: str, payload: dict) -> None:
        """
        Gửi một chat job lên Kafka.

        Args:
            job_id:     UUID của job (dùng để poll kết quả từ Redis).
            session_id: ID phiên – dùng làm partition key.
            payload:    Dict chứa message, history, session_id, job_id.
        """
        if not self._producer:
            raise RuntimeError("Kafka producer chưa được khởi tạo. Gọi start() trước.")

        full_payload = {**payload, "job_id": job_id, "session_id": session_id}

        try:
            record_metadata = await self._producer.send_and_wait(
                topic = TOPIC_JOBS,
                key   = session_id,      # → hash to partition (0-4)
                value = full_payload,
            )
            logger.debug(
                "Job sent: job_id=%s session=%s partition=%d offset=%d",
                job_id, session_id,
                record_metadata.partition,
                record_metadata.offset,
            )
        except KafkaConnectionError as e:
            logger.error("Kafka connection error khi gửi job %s: %s", job_id, e)
            raise
        except Exception as e:
            logger.error("Kafka send failed cho job %s: %s", job_id, e)
            raise


# ── Singleton ─────────────────────────────────────────────────────────────────
kafka_producer = VinmecKafkaProducer()
