"""
app/tools/vinmec_rag.py – LangChain tool gọi Weaviate RAG cho agent Vinmec.

Tool này được bind vào agent graph để bổ sung:
  - Thông tin chuẩn bị khám theo chuyên khoa
  - Yêu cầu nhịn ăn, giấy tờ, thời gian dự kiến
  - FAQ và hướng dẫn chung của Vinmec
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def search_vinmec_preparation(query: str, top_k: int = 3) -> str:
    """
    Tìm kiếm thông tin chuẩn bị khám tại Vinmec từ cơ sở kiến thức RAG.

    Dùng khi bệnh nhân hỏi về:
    - Cần chuẩn bị gì trước buổi khám (nhịn ăn, giấy tờ, đặt lịch...)
    - Thông tin về chuyên khoa cụ thể (tim mạch, sản, nhi, tiêu hoá...)
    - Quy trình xét nghiệm (xét nghiệm máu, siêu âm, nội soi, MRI...)
    - Câu hỏi thường gặp khi đến Vinmec

    Args:
        query: Câu hỏi hoặc từ khoá tìm kiếm bằng tiếng Việt
               VD: "khám tim mạch cần nhịn ăn không", "giấy tờ khám sản", "xét nghiệm máu chuẩn bị gì"
        top_k: Số kết quả trả về (mặc định 3, tối đa 5)

    Returns:
        Thông tin chuẩn bị khám chi tiết hoặc thông báo không tìm thấy.
    """
    try:
        from app.rag.retrieval import build_rag_context
        context = build_rag_context(query=query, top_k=min(top_k, 5))
        if not context:
            return (
                "Không tìm thấy thông tin phù hợp trong cơ sở kiến thức Vinmec. "
                "Vui lòng gọi tổng đài 1900 54 61 54 để được hỗ trợ."
            )
        return context
    except Exception as exc:
        logger.error("RAG tool error: %s", exc, exc_info=True)
        return (
            "Không thể truy cập cơ sở kiến thức lúc này. "
            "Vui lòng gọi tổng đài Vinmec 1900 54 61 54 để được hỗ trợ."
        )


@tool
def get_specialty_checklist(
    specialty: str,
    has_blood_test: bool = False,
    is_first_visit: bool = True,
) -> str:
    """
    Tạo checklist cá nhân hóa cho bệnh nhân trước buổi khám tại Vinmec.

    Args:
        specialty:       Chuyên khoa cần khám (tiếng Việt hoặc tiếng Anh)
                         VD: "tim mạch", "sản phụ khoa", "nhi", "tiêu hoá", "tổng quát"
        has_blood_test:  Bác sĩ có yêu cầu xét nghiệm máu kèm theo không
        is_first_visit:  Đây có phải lần đầu đến Vinmec không

    Returns:
        Checklist 4 mục: nhịn ăn, giấy tờ, đặt lịch, thời gian dự kiến.
    """
    try:
        from app.rag.retrieval import retrieve_preparation_info
        from app.rag.weaviate_client import COL_SPECIALTY

        query = f"khám {specialty} chuẩn bị nhịn ăn giấy tờ"
        results = retrieve_preparation_info(
            query=query,
            top_k=2,
            collections=[COL_SPECIALTY],
        )

        if not results:
            return _fallback_checklist(specialty, has_blood_test, is_first_visit)

        top = results[0].content
        fasting     = top.get("fasting", "none")
        fasting_hrs = top.get("fasting_hours", 0)
        documents   = top.get("documents", '[]')
        booking     = top.get("booking_required", True)
        duration    = top.get("estimated_duration_min", 60)
        notes       = top.get("notes", "")

        # Điều chỉnh nhịn ăn nếu có xét nghiệm máu
        if has_blood_test and fasting == "none":
            fasting = "required"
            fasting_hrs = 8

        fasting_text = {
            "none":     "✅ Không cần nhịn ăn",
            "partial":  f"⚠️  Nhịn ăn nhẹ {fasting_hrs} tiếng trước khi đến",
            "required": f"🚫 Bắt buộc nhịn ăn {fasting_hrs} tiếng (uống nước lọc vẫn được)",
        }.get(fasting, "Không rõ")

        booking_text = (
            "📅 Nên đặt lịch trước qua app MyVinmec hoặc hotline 1900 54 61 54"
            if booking else
            "🚶 Có thể đến thẳng (vẫn nên đặt lịch để giảm thời gian chờ)"
        )

        first_visit_note = ""
        if is_first_visit:
            first_visit_note = (
                "\n\n💡 **Lần đầu đến Vinmec:** Đến trước giờ hẹn 15-20 phút để "
                "làm thủ tục đăng ký. Tải app MyVinmec để xem kết quả xét nghiệm online."
            )

        checklist = f"""
📋 **CHECKLIST CHUẨN BỊ KHÁM: {top.get('name', specialty).upper()}**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🍽️  **1. Nhịn ăn**
{fasting_text}

📄 **2. Giấy tờ cần mang**
{_format_documents(documents)}

📅 **3. Đặt lịch**
{booking_text}

⏱️  **4. Thời gian dự kiến**
~{duration} phút (nếu đã đặt lịch trước)

📝 **Lưu ý đặc biệt**
{notes}
{first_visit_note}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  *Thông tin mang tính tham khảo. Gọi 1900 54 61 54 để xác nhận.*
""".strip()

        return checklist

    except Exception as exc:
        logger.error("Checklist tool error: %s", exc, exc_info=True)
        return _fallback_checklist(specialty, has_blood_test, is_first_visit)


def _format_documents(docs_json: str) -> str:
    """Chuyển JSON array thành danh sách có ký hiệu."""
    import json
    try:
        docs = json.loads(docs_json)
        return "\n".join(f"  • {d}" for d in docs)
    except Exception:
        return f"  • {docs_json}"


def _fallback_checklist(specialty: str, has_blood_test: bool, is_first_visit: bool) -> str:
    """Fallback khi Weaviate không khả dụng."""
    fasting = "🚫 Nhịn ăn 8 tiếng nếu có xét nghiệm máu" if has_blood_test else "✅ Thông thường không cần nhịn ăn"
    return f"""
📋 **CHECKLIST CƠ BẢN – {specialty.upper()}**

🍽️  **1. Nhịn ăn:** {fasting}
📄 **2. Giấy tờ:** CMND/CCCD, Thẻ BHYT (nếu có), Hồ sơ bệnh án cũ
📅 **3. Đặt lịch:** Nên đặt lịch trước qua 1900 54 61 54 hoặc app MyVinmec
⏱️  **4. Thời gian:** ~60-90 phút

⚠️  *Gọi 1900 54 61 54 để xác nhận thông tin chính xác cho trường hợp của bạn.*
""".strip()


# ── Export all tools ──────────────────────────────────────────────────────────
VINMEC_RAG_TOOLS = [search_vinmec_preparation, get_specialty_checklist]
