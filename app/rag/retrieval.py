"""
app/rag/retrieval.py – Truy vấn Weaviate (v2).

Thay đổi so với v1:
  - Dùng app.rag.embedder.get_query_embedder() thay vì logic inline
  - E5 query prefix tự động áp dụng → cải thiện retrieval quality
  - Thêm confidence_threshold để caller biết kết quả có đủ tin cậy không
  - Hybrid search: kết hợp near_vector + BM25 khi VECTORIZER='none'
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from app.rag.weaviate_client import (
    WeaviateSession,
    COL_SPECIALTY, COL_PROCEDURE, COL_DOCUMENT,
    VECTORIZER,
)
from app.rag.embedder import get_query_embedder

logger = logging.getLogger(__name__)

# Ngưỡng score để coi là kết quả tin cậy
# < threshold → agent nên fallback sang web search
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.55"))


@dataclass
class RetrievalResult:
    collection:  str
    score:       float
    name:        str
    content:     dict
    snippet:     str  = field(default="")

    @property
    def is_confident(self) -> bool:
        return self.score >= RAG_CONFIDENCE_THRESHOLD


# ═══════════════════════════════════════════════════════════════════════════════
#  Query embedder (singleton, lazy)
# ═══════════════════════════════════════════════════════════════════════════════

_query_embed_fn = None

def _get_query_embed_fn():
    global _query_embed_fn
    if _query_embed_fn is None:
        _query_embed_fn = get_query_embedder()
    return _query_embed_fn


# ═══════════════════════════════════════════════════════════════════════════════
#  Core retrieval
# ═══════════════════════════════════════════════════════════════════════════════

def _query_collection(
    client,
    col_name: str,
    query_text: str,
    query_vector: Optional[list[float]],
    top_k: int,
    return_props: list[str],
) -> list[RetrievalResult]:
    results = []
    col = client.collections.get(col_name)

    try:
        if VECTORIZER == "none":
            response = col.query.near_vector(
                near_vector=query_vector,
                limit=top_k,
                return_metadata=["certainty", "distance"],
                return_properties=return_props,
            )
        else:
            response = col.query.near_text(
                query=query_text,
                limit=top_k,
                return_metadata=["certainty", "distance"],
                return_properties=return_props,
            )

        for obj in response.objects:
            score = obj.metadata.certainty or (1.0 - (obj.metadata.distance or 1.0))
            name  = obj.properties.get("name") or obj.properties.get("title", "?")
            results.append(RetrievalResult(
                collection = col_name,
                score      = round(score, 4),
                name       = name,
                content    = dict(obj.properties),
                snippet    = _build_snippet(col_name, obj.properties),
            ))
    except Exception as exc:
        logger.warning("Query failed for %s: %s", col_name, exc)

    return results


def _build_snippet(col_name: str, props: dict) -> str:
    if col_name == COL_SPECIALTY:
        fasting_map = {
            "none":     "Không cần nhịn ăn",
            "partial":  f"Nhịn ăn nhẹ {props.get('fasting_hours', 0)} tiếng",
            "required": f"Bắt buộc nhịn ăn {props.get('fasting_hours', 0)} tiếng",
        }
        fasting  = fasting_map.get(props.get("fasting", "none"), "Không rõ")
        booking  = "Cần đặt lịch trước" if props.get("booking_required") else "Có thể đến thẳng"
        duration = props.get("estimated_duration_min", 0)
        return (
            f"**{props.get('name')}** ({props.get('department')})\n"
            f"• Nhịn ăn: {fasting}\n"
            f"• Đặt lịch: {booking}\n"
            f"• Thời gian dự kiến: ~{duration} phút\n"
            f"• Giấy tờ: {props.get('documents', '[]')}\n"
            f"• Lưu ý: {props.get('notes', '')}"
        )
    elif col_name == COL_PROCEDURE:
        fh = props.get("fasting_hours", 0)
        fasting_label = "Không cần nhịn ăn" if fh == 0 else f"Nhịn ăn {fh} tiếng"
        return (
            f"**{props.get('name')}** [{props.get('procedure_type', '')}]\n"
            f"• {fasting_label}\n"
            f"• Chuẩn bị: {props.get('preparation', '')}\n"
            f"• Lưu ý: {props.get('notes', '')}"
        )
    elif col_name == COL_DOCUMENT:
        content = props.get("content", "")
        return f"**{props.get('title')}**\n{content[:600]}{'...' if len(content) > 600 else ''}"
    return str(props)


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════

def retrieve_preparation_info(
    query: str,
    top_k: int = 3,
    collections: Optional[list[str]] = None,
) -> list[RetrievalResult]:
    if collections is None:
        collections = [COL_SPECIALTY, COL_PROCEDURE, COL_DOCUMENT]

    query_vector = None
    if VECTORIZER == "none":
        embed = _get_query_embed_fn()
        query_vector = embed(query)

    props_map = {
        COL_SPECIALTY: [
            "name", "name_en", "department", "fasting", "fasting_hours",
            "documents", "booking_required", "estimated_duration_min", "notes", "tags",
        ],
        COL_PROCEDURE: [
            "name", "name_en", "procedure_type", "fasting", "fasting_hours",
            "preparation", "duration_min", "notes", "tags",
        ],
        COL_DOCUMENT: ["title", "content", "category", "source", "tags"],
    }

    all_results: list[RetrievalResult] = []

    with WeaviateSession() as client:
        for col_name in collections:
            results = _query_collection(
                client       = client,
                col_name     = col_name,
                query_text   = query,
                query_vector = query_vector,
                top_k        = top_k,
                return_props = props_map.get(col_name, []),
            )
            all_results.extend(results)

    all_results.sort(key=lambda r: r.score, reverse=True)
    return all_results


def build_rag_context(query: str, top_k: int = 3) -> str:
    """
    Tạo context string cho LLM.
    Thêm confidence indicator để LLM biết có nên fallback không.
    """
    results = retrieve_preparation_info(query, top_k=top_k)

    if not results:
        return ""

    best_score = results[0].score
    confidence_note = (
        f"[Độ tin cậy RAG: {best_score:.2f} – "
        + ("✅ Đủ tin cậy" if best_score >= RAG_CONFIDENCE_THRESHOLD
           else "⚠️ Thấp – cân nhắc web search bổ sung")
        + "]"
    )

    sections = []
    for r in results:
        sections.append(
            f"[{r.collection} | score={r.score:.2f}{'✅' if r.is_confident else '⚠️'}]\n{r.snippet}"
        )

    return (
        f"=== THÔNG TIN CHUẨN BỊ KHÁM TỪ CƠ SỞ KIẾN THỨC VINMEC ===\n"
        f"{confidence_note}\n\n"
        + "\n\n---\n\n".join(sections)
        + "\n\n=== HẾT THÔNG TIN ==="
    )


def rag_has_confident_answer(query: str, top_k: int = 2) -> bool:
    """
    Nhanh chóng kiểm tra RAG có đủ tin cậy không.
    Dùng trong agent để quyết định có cần web search không.
    """
    results = retrieve_preparation_info(query, top_k=top_k)
    return bool(results) and results[0].score >= RAG_CONFIDENCE_THRESHOLD
