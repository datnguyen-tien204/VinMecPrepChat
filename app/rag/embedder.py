"""
app/rag/embedder.py – Centralized embedding module cho Vinmec RAG.

Thay thế local SentenceTransformer bằng Jina Embeddings API để:
  - bỏ hẳn chi phí load model local lúc startup
  - giảm RAM footprint trên API/worker containers
  - dùng cùng một backend embedding cho query + document
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Callable

import requests

from app.core.config import (
    JINA_API_KEY,
    JINA_EMBEDDING_DIMENSIONS,
    JINA_EMBEDDING_ENDPOINT,
    JINA_EMBEDDING_MODEL,
    JINA_EMBEDDING_NORMALIZED,
    JINA_EMBEDDING_TASK_DOCUMENT,
    JINA_EMBEDDING_TASK_QUERY,
)

logger = logging.getLogger(__name__)
EMBEDDING_PROVIDER = "jina"
REQUEST_TIMEOUT_S = 30
MAX_BATCH_SIZE = 64


@lru_cache(maxsize=1)
def _get_jina_session() -> requests.Session:
    if not JINA_API_KEY:
        raise RuntimeError("JINA_API_KEY chưa được cấu hình.")

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {JINA_API_KEY}",
            "Content-Type": "application/json",
        }
    )
    logger.info("Jina embedding session initialized: model=%s endpoint=%s", JINA_EMBEDDING_MODEL, JINA_EMBEDDING_ENDPOINT)
    return session


def _embed_batch(inputs: list[str], *, task: str) -> list[list[float]]:
    session = _get_jina_session()
    payload = {
        "model": JINA_EMBEDDING_MODEL,
        "task": task,
        "normalized": JINA_EMBEDDING_NORMALIZED,
        "dimensions": JINA_EMBEDDING_DIMENSIONS,
        "embedding_type": "float",
        "input": inputs,
    }
    response = session.post(JINA_EMBEDDING_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    data = response.json().get("data", [])
    if len(data) != len(inputs):
        raise RuntimeError(f"Jina embeddings trả về {len(data)} vectors cho {len(inputs)} inputs.")

    vectors = [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
    return vectors


def _embed_many(inputs: list[str], *, task: str) -> list[list[float]]:
    vectors: list[list[float]] = []
    for i in range(0, len(inputs), MAX_BATCH_SIZE):
        chunk = inputs[i : i + MAX_BATCH_SIZE]
        vectors.extend(_embed_batch(chunk, task=task))
    return vectors


def _embed_one(text: str, *, task: str) -> list[float]:
    return _embed_batch([text], task=task)[0]


@lru_cache(maxsize=1)
def get_document_embedder() -> Callable[[str], list[float]]:
    """Trả về hàm embed(text) → list[float] cho document/passages."""

    def embed_doc(text: str) -> list[float]:
        return _embed_one(text, task=JINA_EMBEDDING_TASK_DOCUMENT)

    logger.info(
        "Document embedder: provider=%s | model=%s | task=%s | dim=%s",
        EMBEDDING_PROVIDER, JINA_EMBEDDING_MODEL, JINA_EMBEDDING_TASK_DOCUMENT, JINA_EMBEDDING_DIMENSIONS,
    )
    return embed_doc


@lru_cache(maxsize=1)
def get_query_embedder() -> Callable[[str], list[float]]:
    """Trả về hàm embed(query) → list[float] cho retrieval queries."""

    def embed_query(text: str) -> list[float]:
        return _embed_one(text, task=JINA_EMBEDDING_TASK_QUERY)

    logger.info(
        "Query embedder: provider=%s | model=%s | task=%s | dim=%s",
        EMBEDDING_PROVIDER, JINA_EMBEDDING_MODEL, JINA_EMBEDDING_TASK_QUERY, JINA_EMBEDDING_DIMENSIONS,
    )
    return embed_query


# ═══════════════════════════════════════════════════════════════════════════════
#  Convenience: batch embed (dùng cho ingest)
# ═══════════════════════════════════════════════════════════════════════════════

def batch_embed_documents(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Embed nhiều document cùng lúc qua Jina API.
    `batch_size` được giữ để tương thích call-site cũ.
    """
    batch_size = max(1, min(batch_size, MAX_BATCH_SIZE))
    all_vecs: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        all_vecs.extend(_embed_many(chunk, task=JINA_EMBEDDING_TASK_DOCUMENT))
    return all_vecs


def warmup_embedding_backend() -> dict:
    """
    Chủ động warmup embedding backend lúc startup.
    Sau warmup, mọi request trong cùng process sẽ reuse HTTP session đã cache.
    """
    _get_jina_session()
    return embedding_info()


# ── Quick info ────────────────────────────────────────────────────────────────
def embedding_info() -> dict:
    """Trả về thông tin model hiện tại để log/debug."""
    return {
        "provider":            EMBEDDING_PROVIDER,
        "model":               JINA_EMBEDDING_MODEL,
        "dimension":           JINA_EMBEDDING_DIMENSIONS,
        "normalized":          JINA_EMBEDDING_NORMALIZED,
        "query_task":          JINA_EMBEDDING_TASK_QUERY,
        "document_task":       JINA_EMBEDDING_TASK_DOCUMENT,
    }
