"""
app/rag/weaviate_client.py – Weaviate v4 client + schema bootstrap cho Vinmec RAG.

Collections:
  VinmecSpecialty      – Thông tin chuyên khoa, yêu cầu chuẩn bị
  VinmecProcedure      – Quy trình xét nghiệm / thủ thuật cụ thể
  VinmecDocument       – Tài liệu hướng dẫn chung (FAQ, lưu ý bệnh viện)
  VinmecFeedback       – Like/dislike theo turn từ người dùng (dùng cho training)
  VinmecFeedbackEnd    – Feedback cuối phiên chat (rating 1-5 sao + comment + tags)
"""
from __future__ import annotations

import logging
import os
from typing import Optional
from urllib.parse import urlparse

import weaviate
from weaviate.classes.config import Configure, DataType, Property, VectorDistances
from weaviate.classes.init import Auth

logger = logging.getLogger(__name__)


# ── Config từ env ─────────────────────────────────────────────────────────────

def _clean_env(key: str, default: str = "") -> str:
    raw     = os.getenv(key, default)
    value   = raw.split("#", 1)[0].strip()
    cleaned = "".join(ch for ch in value if 32 <= ord(ch) <= 126)
    return cleaned.strip()


def _clean_int_env(key: str, default: int) -> int:
    raw = _clean_env(key, str(default))
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r. Fallback to %d", key, raw, default)
        return default


def _parse_weaviate_url(url: str) -> tuple[str, int, bool]:
    cleaned = _clean_env("WEAVIATE_URL", url)
    parsed  = urlparse(cleaned if "://" in cleaned else f"http://{cleaned}")

    host   = (parsed.hostname or "localhost").strip()
    port   = parsed.port or (443 if parsed.scheme == "https" else 8079)
    secure = parsed.scheme == "https"

    if not host:
        raise ValueError(f"Invalid WEAVIATE_URL: {cleaned!r}")

    return host, port, secure


WEAVIATE_URL     = _clean_env("WEAVIATE_URL", "http://localhost:8079")
WEAVIATE_API_KEY = _clean_env("WEAVIATE_API_KEY")
OPENAI_API_KEY   = _clean_env("OPENAI_API_KEY") or _clean_env("OPENAI_APIKEY")
COHERE_API_KEY   = _clean_env("COHERE_API_KEY") or _clean_env("COHERE_APIKEY")

os.environ["WEAVIATE_URL"]      = WEAVIATE_URL
os.environ["WEAVIATE_API_KEY"]  = WEAVIATE_API_KEY
os.environ["OPENAI_API_KEY"]    = OPENAI_API_KEY
os.environ["OPENAI_APIKEY"]     = OPENAI_API_KEY
os.environ["COHERE_API_KEY"]    = COHERE_API_KEY
os.environ["COHERE_APIKEY"]     = COHERE_API_KEY

VECTORIZER = os.getenv("WEAVIATE_VECTORIZER", "none").lower()

# ── Collection names ──────────────────────────────────────────────────────────
COL_SPECIALTY    = "VinmecSpecialty"
COL_PROCEDURE    = "VinmecProcedure"
COL_DOCUMENT     = "VinmecDocument"
COL_FEEDBACK     = "VinmecFeedback"
COL_FEEDBACK_END = "VinmecFeedbackEnd"

ALL_COLLECTIONS = [
    COL_SPECIALTY,
    COL_PROCEDURE,
    COL_DOCUMENT,
    COL_FEEDBACK,
    COL_FEEDBACK_END,
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Client factory
# ═══════════════════════════════════════════════════════════════════════════════

def get_client() -> weaviate.WeaviateClient:
    headers: dict[str, str] = {}
    if OPENAI_API_KEY:
        headers["X-OpenAI-Api-Key"] = OPENAI_API_KEY
    if COHERE_API_KEY:
        headers["X-Cohere-Api-Key"] = COHERE_API_KEY

    http_host, http_port, http_secure = _parse_weaviate_url(WEAVIATE_URL)

    grpc_host   = _clean_env("WEAVIATE_GRPC_HOST", "localhost") or "localhost"
    grpc_port   = _clean_int_env("WEAVIATE_GRPC_PORT", 50051)
    grpc_secure = (_clean_env("WEAVIATE_GRPC_SECURE", "false").lower() == "true")

    auth = Auth.api_key(WEAVIATE_API_KEY) if WEAVIATE_API_KEY else None

    client = weaviate.connect_to_custom(
        http_host        = http_host,
        http_port        = http_port,
        http_secure      = http_secure,
        grpc_host        = grpc_host,
        grpc_port        = grpc_port,
        grpc_secure      = grpc_secure,
        auth_credentials = auth,
        headers          = headers,
    )
    return client


# ═══════════════════════════════════════════════════════════════════════════════
#  Schema bootstrap
# ═══════════════════════════════════════════════════════════════════════════════

def _vectorizer_config():
    if VECTORIZER == "openai":
        return Configure.Vectorizer.text2vec_openai()
    elif VECTORIZER == "cohere":
        return Configure.Vectorizer.text2vec_cohere()
    else:
        return Configure.Vectorizer.none()


def _create_specialty_collection(client: weaviate.WeaviateClient) -> None:
    client.collections.create(
        name = COL_SPECIALTY,
        vectorizer_config  = _vectorizer_config(),
        vector_index_config = Configure.VectorIndex.hnsw(
            distance_metric = VectorDistances.COSINE,
        ),
        properties = [
            Property(name="name",                    data_type=DataType.TEXT),
            Property(name="name_en",                 data_type=DataType.TEXT),
            Property(name="department",              data_type=DataType.TEXT),
            Property(name="fasting",                 data_type=DataType.TEXT),
            Property(name="fasting_hours",           data_type=DataType.INT),
            Property(name="documents",               data_type=DataType.TEXT),
            Property(name="booking_required",        data_type=DataType.BOOL),
            Property(name="estimated_duration_min",  data_type=DataType.INT),
            Property(name="notes",                   data_type=DataType.TEXT),
            Property(name="tags",                    data_type=DataType.TEXT_ARRAY),
        ],
    )
    logger.info("Created collection: %s", COL_SPECIALTY)


def _create_procedure_collection(client: weaviate.WeaviateClient) -> None:
    client.collections.create(
        name = COL_PROCEDURE,
        vectorizer_config  = _vectorizer_config(),
        vector_index_config = Configure.VectorIndex.hnsw(
            distance_metric = VectorDistances.COSINE,
        ),
        properties = [
            Property(name="name",              data_type=DataType.TEXT),
            Property(name="name_en",           data_type=DataType.TEXT),
            Property(name="procedure_type",    data_type=DataType.TEXT),
            Property(name="fasting",           data_type=DataType.TEXT),
            Property(name="fasting_hours",     data_type=DataType.INT),
            Property(name="preparation",       data_type=DataType.TEXT),
            Property(name="duration_min",      data_type=DataType.INT),
            Property(name="contraindications", data_type=DataType.TEXT),
            Property(name="notes",             data_type=DataType.TEXT),
            Property(name="tags",              data_type=DataType.TEXT_ARRAY),
        ],
    )
    logger.info("Created collection: %s", COL_PROCEDURE)


def _create_document_collection(client: weaviate.WeaviateClient) -> None:
    client.collections.create(
        name = COL_DOCUMENT,
        vectorizer_config  = _vectorizer_config(),
        vector_index_config = Configure.VectorIndex.hnsw(
            distance_metric = VectorDistances.COSINE,
        ),
        properties = [
            Property(name="title",    data_type=DataType.TEXT),
            Property(name="content",  data_type=DataType.TEXT),
            Property(name="category", data_type=DataType.TEXT),
            Property(name="source",   data_type=DataType.TEXT),
            Property(name="tags",     data_type=DataType.TEXT_ARRAY),
        ],
    )
    logger.info("Created collection: %s", COL_DOCUMENT)


def _create_feedback_collection(client: weaviate.WeaviateClient) -> None:
    """
    VinmecFeedback – like/dislike theo turn, kèm toàn bộ lịch sử chat.

    Fields:
      session_id   – ID phiên chat
      rating       – 'like' hoặc 'dislike'
      messages     – JSON string của list[{role, content}]
      user_comment – Ghi chú tuỳ chọn của người dùng
      turn_count   – Số lượt trao đổi trong phiên
      full_text    – Nội dung hội thoại ghép lại (dùng để vectorize)
      created_at   – ISO timestamp UTC
    """
    client.collections.create(
        name = COL_FEEDBACK,
        vectorizer_config  = _vectorizer_config(),
        vector_index_config = Configure.VectorIndex.hnsw(
            distance_metric = VectorDistances.COSINE,
        ),
        properties = [
            Property(name="session_id",   data_type=DataType.TEXT),
            Property(name="rating",       data_type=DataType.TEXT),
            Property(name="messages",     data_type=DataType.TEXT),
            Property(name="user_comment", data_type=DataType.TEXT),
            Property(name="turn_count",   data_type=DataType.INT),
            Property(name="full_text",    data_type=DataType.TEXT),
            Property(name="created_at",   data_type=DataType.TEXT),
        ],
    )
    logger.info("Created collection: %s", COL_FEEDBACK)


def _create_feedback_end_collection(client: weaviate.WeaviateClient) -> None:
    """
    VinmecFeedbackEnd – Feedback cuối phiên chat (end-of-session survey).

    Khác với VinmecFeedback (like/dislike theo turn), collection này lưu
    đánh giá tổng thể sau khi người dùng kết thúc cuộc trò chuyện.

    Fields:
      session_id    – ID phiên chat
      rating        – Điểm số 1-5 sao (INT)
      comment       – Nhận xét văn bản tuỳ chọn của người dùng
      tags          – Danh mục đánh giá: ["helpful", "accurate", "fast", ...]
      turn_count    – Số lượt trao đổi trong phiên
      full_text     – Nội dung toàn bộ hội thoại ghép lại (dùng để vectorize)
      created_at    – ISO timestamp UTC
    """
    client.collections.create(
        name = COL_FEEDBACK_END,
        vectorizer_config  = _vectorizer_config(),
        vector_index_config = Configure.VectorIndex.hnsw(
            distance_metric = VectorDistances.COSINE,
        ),
        properties = [
            Property(name="session_id",  data_type=DataType.TEXT),
            Property(name="rating",      data_type=DataType.INT),
            Property(name="comment",     data_type=DataType.TEXT),
            Property(name="tags",        data_type=DataType.TEXT_ARRAY),
            Property(name="turn_count",  data_type=DataType.INT),
            Property(name="full_text",   data_type=DataType.TEXT),
            Property(name="created_at",  data_type=DataType.TEXT),
        ],
    )
    logger.info("Created collection: %s", COL_FEEDBACK_END)


def bootstrap_schema(client: weaviate.WeaviateClient, force: bool = False) -> None:
    existing = {c.name for c in client.collections.list_all().values()}

    creators = {
        COL_SPECIALTY:    _create_specialty_collection,
        COL_PROCEDURE:    _create_procedure_collection,
        COL_DOCUMENT:     _create_document_collection,
        COL_FEEDBACK:     _create_feedback_collection,
        COL_FEEDBACK_END: _create_feedback_end_collection,
    }

    for col_name in ALL_COLLECTIONS:
        if col_name in existing:
            if force:
                client.collections.delete(col_name)
                logger.warning("Dropped collection: %s (force=True)", col_name)
            else:
                logger.info("Collection already exists, skipping: %s", col_name)
                continue
        creators[col_name](client)

    logger.info("Schema bootstrap complete.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Context manager helper
# ═══════════════════════════════════════════════════════════════════════════════

class WeaviateSession:
    def __init__(self):
        self._client: Optional[weaviate.WeaviateClient] = None

    def __enter__(self) -> weaviate.WeaviateClient:
        self._client = get_client()
        return self._client

    def __exit__(self, *_):
        if self._client:
            self._client.close()
