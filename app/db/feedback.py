"""
app/db/feedback.py – Lưu feedback vào Weaviate.

Collections:
  VinmecFeedback     – like/dislike theo turn kèm lịch sử chat
  VinmecFeedbackEnd  – Đánh giá tổng thể cuối phiên (1-5 sao + tags + comment)

FIXES vs v1:
  [BUG-1] return_metadata=[\"creation_time\"] / [\"certainty\"] → sai Weaviate v4 API.
          Phải dùng MetadataQuery object.
  [BUG-2] asyncio.get_event_loop() deprecated Python 3.10+ → dùng get_running_loop() ở server.py
  [BUG-3] Không có dedup check → thêm _feedback_exists() kiểm tra trước insert.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from weaviate.classes.query import Filter, MetadataQuery

from app.rag.weaviate_client import (
    WeaviateSession,
    COL_FEEDBACK,
    COL_FEEDBACK_END,
    VECTORIZER,
)
from app.rag.embedder import get_document_embedder

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_full_text(messages: list[dict]) -> str:
    """Ghép toàn bộ lịch sử chat thành một chuỗi văn bản để embed."""
    lines = []
    for m in messages:
        role    = "Người dùng" if m.get("role") == "user" else "Trợ lý"
        content = m.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _feedback_exists(col, session_id: str, rating: str) -> bool:
    """
    [BUG-3 FIX] Kiểm tra xem session đã có feedback với rating này chưa.
    Ngăn user spam like/dislike nhiều lần cho cùng một session.
    """
    try:
        resp = col.query.fetch_objects(
            filters=(
                Filter.by_property("session_id").equal(session_id) &
                Filter.by_property("rating").equal(rating)
            ),
            limit=1,
            return_properties=["session_id"],
        )
        return len(resp.objects) > 0
    except Exception as e:
        logger.warning("Dedup check failed (cho phép insert): %s", e)
        return False


def _feedback_end_exists(col, session_id: str) -> bool:
    """Kiểm tra session đã có feedback_end chưa (mỗi session chỉ được submit 1 lần)."""
    try:
        resp = col.query.fetch_objects(
            filters=Filter.by_property("session_id").equal(session_id),
            limit=1,
            return_properties=["session_id"],
        )
        return len(resp.objects) > 0
    except Exception as e:
        logger.warning("FeedbackEnd dedup check failed (cho phép insert): %s", e)
        return False


# ── VinmecFeedback (like / dislike per turn) ───────────────────────────────────

def save_feedback(
    session_id:   str,
    rating:       str,
    messages:     list[dict],
    user_comment: Optional[str] = None,
) -> str:
    """
    Lưu một bản ghi feedback like/dislike vào Weaviate.

    Raises:
        ValueError: Nếu session đã có feedback với cùng rating (dedup).
    """
    full_text    = _build_full_text(messages)
    messages_str = json.dumps(messages, ensure_ascii=False)
    created_at   = datetime.now(timezone.utc).isoformat()

    properties = {
        "session_id":   session_id,
        "rating":       rating,
        "messages":     messages_str,
        "user_comment": user_comment or "",
        "turn_count":   len(messages),
        "full_text":    full_text,
        "created_at":   created_at,
    }

    with WeaviateSession() as client:
        col = client.collections.get(COL_FEEDBACK)

        if _feedback_exists(col, session_id, rating):
            raise ValueError(
                f"Session '{session_id}' đã có feedback '{rating}'. "
                "Không thể submit lại cùng rating."
            )

        if VECTORIZER == "none":
            embedder = get_document_embedder()
            vector   = embedder(full_text)
            obj_uuid = col.data.insert(properties=properties, vector=vector)
        else:
            obj_uuid = col.data.insert(properties=properties)

    logger.info(
        "Feedback saved: uuid=%s session=%s rating=%s turns=%d",
        obj_uuid, session_id, rating, len(messages),
    )
    return str(obj_uuid)


def get_feedback(
    rating: Optional[str] = None,
    limit:  int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    Lấy danh sách feedback để trainer review.
    [BUG-1 FIX] return_metadata dùng MetadataQuery thay vì list[str].
    """
    with WeaviateSession() as client:
        col = client.collections.get(COL_FEEDBACK)

        kwargs: dict = dict(
            limit             = limit,
            offset            = offset,
            return_properties = [
                "session_id", "rating", "messages",
                "user_comment", "turn_count", "created_at",
            ],
            return_metadata   = MetadataQuery(creation_time=True),
        )

        if rating in ("like", "dislike"):
            kwargs["filters"] = Filter.by_property("rating").equal(rating)

        response = col.query.fetch_objects(**kwargs)

    results = []
    for obj in response.objects:
        p = obj.properties
        results.append({
            "uuid":         str(obj.uuid),
            "session_id":   p.get("session_id"),
            "rating":       p.get("rating"),
            "messages":     json.loads(p.get("messages", "[]")),
            "user_comment": p.get("user_comment"),
            "turn_count":   p.get("turn_count"),
            "created_at":   p.get("created_at"),
        })

    return results


def search_feedback(
    query:  str,
    rating: Optional[str] = None,
    limit:  int = 20,
) -> list[dict]:
    """
    Semantic search qua các đoạn hội thoại đã feedback.
    [BUG-1 FIX] return_metadata dùng MetadataQuery(certainty=True).
    """
    with WeaviateSession() as client:
        col = client.collections.get(COL_FEEDBACK)

        filters = None
        if rating in ("like", "dislike"):
            filters = Filter.by_property("rating").equal(rating)

        common_props = [
            "session_id", "rating", "messages",
            "user_comment", "turn_count", "created_at",
        ]
        meta = MetadataQuery(certainty=True)

        if VECTORIZER == "none":
            embedder     = get_document_embedder()
            query_vector = embedder(query)
            response     = col.query.near_vector(
                near_vector       = query_vector,
                limit             = limit,
                filters           = filters,
                return_properties = common_props,
                return_metadata   = meta,
            )
        else:
            response = col.query.near_text(
                query             = query,
                limit             = limit,
                filters           = filters,
                return_properties = common_props,
                return_metadata   = meta,
            )

    results = []
    for obj in response.objects:
        p = obj.properties
        results.append({
            "uuid":         str(obj.uuid),
            "session_id":   p.get("session_id"),
            "rating":       p.get("rating"),
            "messages":     json.loads(p.get("messages", "[]")),
            "user_comment": p.get("user_comment"),
            "turn_count":   p.get("turn_count"),
            "created_at":   p.get("created_at"),
            "score":        round(obj.metadata.certainty or 0.0, 4),
        })

    return results


def count_feedback() -> dict:
    """Đếm tổng số feedback like/dislike. Dùng cho dashboard trainer."""
    with WeaviateSession() as client:
        col = client.collections.get(COL_FEEDBACK)

        total    = col.aggregate.over_all(total_count=True).total_count
        likes    = col.aggregate.over_all(
            total_count = True,
            filters     = Filter.by_property("rating").equal("like"),
        ).total_count
        dislikes = col.aggregate.over_all(
            total_count = True,
            filters     = Filter.by_property("rating").equal("dislike"),
        ).total_count

    return {
        "total":   total    or 0,
        "like":    likes    or 0,
        "dislike": dislikes or 0,
    }


# ── VinmecFeedbackEnd (end-of-session survey) ──────────────────────────────────

def save_feedback_end(
    session_id: str,
    rating:     int,
    messages:   list[dict],
    comment:    Optional[str] = None,
    tags:       Optional[list[str]] = None,
) -> str:
    """
    Lưu đánh giá tổng thể cuối phiên chat vào VinmecFeedbackEnd.

    Args:
        session_id : ID phiên chat
        rating     : Điểm 1-5 sao
        messages   : Toàn bộ lịch sử hội thoại
        comment    : Nhận xét văn bản tuỳ chọn
        tags       : Danh mục đánh giá, vd ["helpful", "accurate", "fast"]

    Raises:
        ValueError: Nếu session đã có feedback_end (mỗi session chỉ được submit 1 lần).
    """
    if not (1 <= rating <= 5):
        raise ValueError(f"Rating phải từ 1 đến 5, nhận được: {rating}")

    full_text  = _build_full_text(messages)
    created_at = datetime.now(timezone.utc).isoformat()

    properties = {
        "session_id": session_id,
        "rating":     rating,
        "comment":    comment or "",
        "tags":       tags or [],
        "turn_count": len(messages),
        "full_text":  full_text,
        "created_at": created_at,
    }

    with WeaviateSession() as client:
        col = client.collections.get(COL_FEEDBACK_END)

        if _feedback_end_exists(col, session_id):
            raise ValueError(
                f"Session '{session_id}' đã có feedback cuối phiên. "
                "Không thể submit lại."
            )

        if VECTORIZER == "none":
            embedder = get_document_embedder()
            vector   = embedder(full_text)
            obj_uuid = col.data.insert(properties=properties, vector=vector)
        else:
            obj_uuid = col.data.insert(properties=properties)

    logger.info(
        "FeedbackEnd saved: uuid=%s session=%s rating=%d turns=%d tags=%s",
        obj_uuid, session_id, rating, len(messages), tags,
    )
    return str(obj_uuid)


def get_feedback_end(
    rating: Optional[int] = None,
    limit:  int = 50,
    offset: int = 0,
) -> list[dict]:
    """Lấy danh sách feedback cuối phiên. Trainer dùng để phân tích NPS / CSAT."""
    with WeaviateSession() as client:
        col = client.collections.get(COL_FEEDBACK_END)

        kwargs: dict = dict(
            limit             = limit,
            offset            = offset,
            return_properties = [
                "session_id", "rating", "comment",
                "tags", "turn_count", "created_at",
            ],
            return_metadata   = MetadataQuery(creation_time=True),
        )

        if rating is not None and 1 <= rating <= 5:
            kwargs["filters"] = Filter.by_property("rating").equal(rating)

        response = col.query.fetch_objects(**kwargs)

    results = []
    for obj in response.objects:
        p = obj.properties
        results.append({
            "uuid":       str(obj.uuid),
            "session_id": p.get("session_id"),
            "rating":     p.get("rating"),
            "comment":    p.get("comment"),
            "tags":       p.get("tags") or [],
            "turn_count": p.get("turn_count"),
            "created_at": p.get("created_at"),
        })

    return results


def count_feedback_end() -> dict:
    """
    Thống kê feedback cuối phiên theo từng mức sao.
    Trả về total, avg_rating và breakdown từng sao (1-5).
    """
    with WeaviateSession() as client:
        col = client.collections.get(COL_FEEDBACK_END)

        total = col.aggregate.over_all(total_count=True).total_count or 0

        breakdown: dict[int, int] = {}
        for star in range(1, 6):
            count = col.aggregate.over_all(
                total_count = True,
                filters     = Filter.by_property("rating").equal(star),
            ).total_count or 0
            breakdown[star] = count

    weighted_sum = sum(star * cnt for star, cnt in breakdown.items())
    avg_rating   = round(weighted_sum / total, 2) if total > 0 else 0.0

    return {
        "total":      total,
        "avg_rating": avg_rating,
        "breakdown":  {f"{star}_star": cnt for star, cnt in breakdown.items()},
    }
