"""
scripts/ingest_medical_data.py – Nhập dữ liệu y tế Vinmec vào Weaviate.  (v2)

Thay đổi so với v1:
  - Dùng app.rag.embedder thay vì logic embedding inline
  - Merge medical_data_extra vào medical_data
  - Batch embed qua Jina Embeddings API
  - In embedding info trước khi ingest để dễ debug

Chạy:
  python scripts/ingest_medical_data.py            # ingest lần đầu
  python scripts/ingest_medical_data.py --reset    # xoá và nhập lại từ đầu
  python scripts/ingest_medical_data.py --verify   # chỉ đếm objects
  python scripts/ingest_medical_data.py --info     # in embedding model info
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rag.weaviate_client import (
    WeaviateSession, bootstrap_schema,
    COL_SPECIALTY, COL_PROCEDURE, COL_DOCUMENT,
    VECTORIZER,
)
from app.rag.medical_data import SPECIALTIES, PROCEDURES, DOCUMENTS
from app.rag.medical_data_extra import SPECIALTIES_EXTRA, PROCEDURES_EXTRA, DOCUMENTS_EXTRA
from app.rag.embedder import (
    get_document_embedder, batch_embed_documents, embedding_info,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Merge dữ liệu base + extra
ALL_SPECIALTIES = SPECIALTIES + SPECIALTIES_EXTRA
ALL_PROCEDURES  = PROCEDURES  + PROCEDURES_EXTRA
ALL_DOCUMENTS   = DOCUMENTS   + DOCUMENTS_EXTRA


# ═══════════════════════════════════════════════════════════════════════════════
#  Text builders (giống v1 nhưng tập trung tại đây)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_specialty_text(item: dict) -> str:
    return "\n".join([
        f"Chuyên khoa: {item['name']}",
        f"Khoa: {item['department']}",
        f"Nhịn ăn: {item['fasting']} ({item['fasting_hours']} tiếng)",
        f"Giấy tờ cần: {item['documents']}",
        f"Đặt lịch bắt buộc: {'Có' if item['booking_required'] else 'Không'}",
        f"Ghi chú: {item['notes']}",
        f"Tags: {', '.join(item['tags'])}",
    ])


def _build_procedure_text(item: dict) -> str:
    return "\n".join([
        f"Xét nghiệm/Thủ thuật: {item['name']}",
        f"Loại: {item['procedure_type']}",
        f"Nhịn ăn: {item['fasting']} ({item['fasting_hours']} tiếng)",
        f"Chuẩn bị: {item['preparation']}",
        f"Ghi chú: {item['notes']}",
        f"Tags: {', '.join(item['tags'])}",
    ])


def _build_document_text(item: dict) -> str:
    return f"Tiêu đề: {item['title']}\n{item['content']}\nTags: {', '.join(item['tags'])}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Ingest
# ═══════════════════════════════════════════════════════════════════════════════

def _ingest_collection(
    collection,
    items: list[dict],
    build_text_fn,
    embed_fn,
) -> int:
    """Ingest một collection. Trả về số objects đã insert."""
    if VECTORIZER != "none":
        # Weaviate managed vectorizer
        with collection.batch.dynamic() as batch:
            for item in items:
                batch.add_object(properties=item)
        return len(items)

    # Manual embedding – batch để nhanh hơn
    texts   = [build_text_fn(item) for item in items]
    vectors = batch_embed_documents(texts)

    inserted = 0
    with collection.batch.dynamic() as batch:
        for item, vector in zip(items, vectors):
            batch.add_object(properties=item, vector=vector)
            inserted += 1

    return inserted


def ingest_all(reset: bool = False) -> None:
    """Nhập toàn bộ dữ liệu y tế (base + extra) vào Weaviate."""
    # Print embedding info
    info = embedding_info()
    logger.info(
        "Embedding config: provider=%s | model=%s | dim=%s | normalized=%s",
        info["provider"], info["model"], info["dimension"], info["normalized"],
    )

    embed_fn = get_document_embedder() if VECTORIZER == "none" else None

    with WeaviateSession() as client:
        bootstrap_schema(client, force=reset)

        for col_name, items, build_fn, label in [
            (COL_SPECIALTY, ALL_SPECIALTIES, _build_specialty_text, "specialties"),
            (COL_PROCEDURE, ALL_PROCEDURES,  _build_procedure_text, "procedures"),
            (COL_DOCUMENT,  ALL_DOCUMENTS,   _build_document_text,  "documents"),
        ]:
            logger.info("Ingesting %d %s...", len(items), label)
            col = client.collections.get(col_name)
            n   = _ingest_collection(col, items, build_fn, embed_fn)
            logger.info("  ✅ Inserted %d %s", n, label)

    logger.info("🎉 Ingestion complete! Total: %d items",
                len(ALL_SPECIALTIES) + len(ALL_PROCEDURES) + len(ALL_DOCUMENTS))


def verify_ingestion() -> None:
    """Kiểm tra số lượng objects đã được nhập."""
    with WeaviateSession() as client:
        total = 0
        for col_name in [COL_SPECIALTY, COL_PROCEDURE, COL_DOCUMENT]:
            col   = client.collections.get(col_name)
            count = col.aggregate.over_all(total_count=True).total_count
            logger.info("  %s: %d objects", col_name, count)
            total += count
        logger.info("  TOTAL: %d objects", total)


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Vinmec medical data into Weaviate (v2)")
    parser.add_argument("--reset",  action="store_true", help="Xoá toàn bộ collections và nhập lại")
    parser.add_argument("--verify", action="store_true", help="Chỉ đếm objects hiện có")
    parser.add_argument("--info",   action="store_true", help="In thông tin embedding model")
    args = parser.parse_args()

    if args.info:
        info = embedding_info()
        print("\nEmbedding model info:")
        for k, v in info.items():
            print(f"  {k}: {v}")
        print()
    elif args.verify:
        verify_ingestion()
    else:
        ingest_all(reset=args.reset)
        verify_ingestion()
