"""
Central production config for VinmecPrep AI.

Everything is loaded from environment variables so the whole service runs from
the `app/` package only.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "VinmecPrep AI"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "2.0.0"))

    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "groq/qwen/qwen3-32b"))
    llm_api_base: str = field(default_factory=lambda: os.getenv("LLM_API_BASE", ""))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", os.getenv("GROQ_API_KEY", "")))
    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.3")))
    llm_max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2048")))

    serper_api_key: str = field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""))
    searxng_url: str = field(default_factory=lambda: os.getenv("SEARXNG_URL", "http://searxng:8080"))
    web_search_top_k: int = field(default_factory=lambda: int(os.getenv("WEB_SEARCH_TOP_K", "5")))

    weaviate_url: str = field(default_factory=lambda: os.getenv("WEAVIATE_URL", "http://weaviate:8080"))
    weaviate_api_key: str = field(default_factory=lambda: os.getenv("WEAVIATE_API_KEY", "").split("#")[0].strip())
    weaviate_grpc_host: str = field(default_factory=lambda: os.getenv("WEAVIATE_GRPC_HOST", "weaviate"))
    weaviate_grpc_port: int = field(default_factory=lambda: int(os.getenv("WEAVIATE_GRPC_PORT", "50051")))
    weaviate_vectorizer: str = field(default_factory=lambda: os.getenv("WEAVIATE_VECTORIZER", "none").lower())

    jina_api_key: str = field(default_factory=lambda: os.getenv("JINA_API_KEY", "").split("#")[0].strip())
    jina_embedding_endpoint: str = field(
        default_factory=lambda: os.getenv("JINA_EMBEDDING_ENDPOINT", "https://api.jina.ai/v1/embeddings").strip()
    )
    jina_embedding_model: str = field(
        default_factory=lambda: os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v5-text-small").strip()
    )
    jina_embedding_dimensions: int = field(
        default_factory=lambda: int(os.getenv("JINA_EMBEDDING_DIMENSIONS", "1024"))
    )
    jina_embedding_normalized: bool = field(
        default_factory=lambda: os.getenv("JINA_EMBEDDING_NORMALIZED", "true").lower() == "true"
    )
    jina_embedding_task_query: str = field(
        default_factory=lambda: os.getenv("JINA_EMBEDDING_TASK_QUERY", "retrieval.query").strip()
    )
    jina_embedding_task_document: str = field(
        default_factory=lambda: os.getenv("JINA_EMBEDDING_TASK_DOCUMENT", "retrieval.passage").strip()
    )

    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0"))
    redis_session_ttl: int = field(default_factory=lambda: int(os.getenv("REDIS_SESSION_TTL", "86400")))
    redis_cache_ttl: int = field(default_factory=lambda: int(os.getenv("REDIS_CACHE_TTL", "300")))

    kafka_bootstrap: str = field(default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"))
    kafka_topic_jobs: str = field(default_factory=lambda: os.getenv("KAFKA_TOPIC_JOBS", "vinmec.chat.jobs"))
    kafka_topic_results: str = field(default_factory=lambda: os.getenv("KAFKA_TOPIC_RESULTS", "vinmec.chat.results"))
    kafka_partitions: int = field(default_factory=lambda: int(os.getenv("KAFKA_PARTITIONS", "5")))

    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "").strip())
    trainer_api_key: str = field(default_factory=lambda: os.getenv("TRAINER_API_KEY", "").strip())
    allowed_origins: List[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:8890,http://localhost:3000",
            ).split(",")
            if origin.strip()
        ]
    )

    rate_limit_rpm: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_RPM", "10")))
    max_input_chars: int = field(default_factory=lambda: int(os.getenv("MAX_INPUT_CHARS", "2000")))
    chat_poll_timeout: int = field(default_factory=lambda: int(os.getenv("CHAT_POLL_TIMEOUT", "45")))

    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", os.getenv("DAILY_BUDGET_USD", "10.0")))
    )
    price_input_per_1m_tokens_usd: float = field(
        default_factory=lambda: float(os.getenv("PRICE_INPUT_PER_1M_TOKENS_USD", "0.27"))
    )
    price_output_per_1m_tokens_usd: float = field(
        default_factory=lambda: float(os.getenv("PRICE_OUTPUT_PER_1M_TOKENS_USD", "0.27"))
    )

    sentry_dsn: str = field(default_factory=lambda: os.getenv("SENTRY_DSN", "").split("#")[0].strip())
    embedding_warmup: bool = field(default_factory=lambda: os.getenv("EMBEDDING_WARMUP", "1") == "1")

    api_workers: int = field(default_factory=lambda: int(os.getenv("API_WORKERS", "4")))
    worker_concurrency: int = field(default_factory=lambda: int(os.getenv("WORKER_CONCURRENCY", "10")))

    def validate(self) -> "Settings":
        logger = logging.getLogger(__name__)
        if self.environment == "production":
            if not self.agent_api_key:
                raise ValueError("AGENT_API_KEY phải được set trong production!")
            if not self.trainer_api_key:
                raise ValueError("TRAINER_API_KEY phải được set trong production!")
            if not self.llm_api_key:
                raise ValueError("LLM_API_KEY phải được set trong production!")
            if self.weaviate_vectorizer == "none" and not self.jina_api_key:
                raise ValueError("JINA_API_KEY phải được set khi WEAVIATE_VECTORIZER=none trong production!")
        if not self.llm_api_key:
            logger.warning("LLM_API_KEY chưa set – sẽ fail khi gọi LLM thật")
        if self.weaviate_vectorizer == "none" and not self.jina_api_key:
            logger.warning("JINA_API_KEY chưa set – manual embeddings sẽ fail")
        return self


settings = Settings().validate()

LLM_MODEL = settings.llm_model
LLM_API_BASE = settings.llm_api_base
LLM_API_KEY = settings.llm_api_key
LLM_TEMPERATURE = settings.llm_temperature
LLM_MAX_TOKENS = settings.llm_max_tokens

SERPER_API_KEY = settings.serper_api_key
SEARXNG_URL = settings.searxng_url
WEB_SEARCH_TOP_K = settings.web_search_top_k

REDIS_URL = settings.redis_url
REDIS_SESSION_TTL = settings.redis_session_ttl
ALLOWED_ORIGINS = settings.allowed_origins
RATE_LIMIT_RPM = settings.rate_limit_rpm
MAX_INPUT_CHARS = settings.max_input_chars
PRICE_INPUT_PER_1M_TOKENS_USD = settings.price_input_per_1m_tokens_usd
PRICE_OUTPUT_PER_1M_TOKENS_USD = settings.price_output_per_1m_tokens_usd

JINA_API_KEY = settings.jina_api_key
JINA_EMBEDDING_ENDPOINT = settings.jina_embedding_endpoint
JINA_EMBEDDING_MODEL = settings.jina_embedding_model
JINA_EMBEDDING_DIMENSIONS = settings.jina_embedding_dimensions
JINA_EMBEDDING_NORMALIZED = settings.jina_embedding_normalized
JINA_EMBEDDING_TASK_QUERY = settings.jina_embedding_task_query
JINA_EMBEDDING_TASK_DOCUMENT = settings.jina_embedding_task_document
