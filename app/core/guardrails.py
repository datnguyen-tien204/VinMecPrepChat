"""
app/core/guardrails.py – Input guardrails cho VinmecPrep AI.

5 lớp bảo vệ:
  0. INPUT SIZE  – giới hạn độ dài input
  1. HARD BLOCK  – nội dung tuyệt đối không trả lời (bạo lực, 18+, jailbreak)
  2. EMERGENCY   – nhận dạng cấp cứu → redirect 115 ngay lập tức
  3. OFF_TOPIC   – câu hỏi không liên quan y tế / Vinmec → từ chối lịch sự
  4. PII WARNING – phát hiện CCCD/SĐT/email → nhắc nhở không chia sẻ
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.core.config import MAX_INPUT_CHARS


class GuardResult(Enum):
    PASS      = "pass"
    BLOCK     = "block"
    EMERGENCY = "emergency"
    OFF_TOPIC = "off_topic"
    PII_WARN  = "pii_warn"
    TOO_LONG  = "too_long"


@dataclass
class GuardOutcome:
    result:  GuardResult
    message: str | None = None


# ── 1. Hard block ─────────────────────────────────────────────────────────────
_HARD_BLOCK_PATTERNS = [
    r"\b(cách giết|cách làm bom|chế tạo vũ khí|cách tự tử|cách chết)\b",
    r"\b(đảo chính|lật đổ chính phủ|jihad|khủng bố)\b",
    r"\b(sex|khiêu dâm|porn|nội dung người lớn)\b",
    r"(ignore previous|forget your instructions|you are now|act as|jailbreak"
    r"|pretend you|your new instructions|system prompt)",
    r"(bypass|override|disable your|turn off your|ignore your (rules|guidelines|restrictions))",
]
_HARD_BLOCK_RE = re.compile("|".join(_HARD_BLOCK_PATTERNS), re.IGNORECASE)

_HARD_BLOCK_MSG = (
    "Xin lỗi, tôi không thể hỗ trợ nội dung này. "
    "Tôi chỉ có thể giúp bạn chuẩn bị cho buổi khám tại Vinmec. "
    "Nếu cần hỗ trợ khẩn cấp, vui lòng gọi **115**."
)

# ── 2. Emergency ──────────────────────────────────────────────────────────────
_EMERGENCY_PATTERNS = [
    r"\b(cấp cứu|khẩn cấp|ngừng tim|ngừng thở|hôn mê|bất tỉnh)\b",
    r"\b(đột quỵ|stroke|nhồi máu cơ tim|heart attack)\b",
    r"\b(chảy máu không cầm|gãy xương hở|tai nạn giao thông nặng)\b",
    r"\b(nuốt phải|uống nhầm thuốc|ngộ độc cấp)\b",
    r"\b(tôi đang chết|tôi không thể thở)\b",
]
_EMERGENCY_RE = re.compile("|".join(_EMERGENCY_PATTERNS), re.IGNORECASE)

_EMERGENCY_MSG = (
    "🚨 **ĐÂY CÓ VẺ LÀ TÌNH HUỐNG KHẨN CẤP!**\n\n"
    "Vui lòng **gọi ngay 115** hoặc đến phòng **Cấp cứu Vinmec** gần nhất.\n\n"
    "Đừng chờ đợi — mỗi giây đều quan trọng trong tình huống cấp cứu.\n\n"
    "_Sau khi ổn định, tôi sẵn sàng hỗ trợ bạn chuẩn bị các buổi khám tiếp theo._"
)

# ── 3. Off-topic detection ────────────────────────────────────────────────────
# Từ khoá Y TẾ / VINMEC / ĐỊA ĐIỂM → nếu có → PASS
_MEDICAL_KEYWORDS = re.compile(
    r"(khám|bệnh|đau|xét nghiệm|máu|siêu âm|mri|ct|x-quang|nội soi"
    r"|thuốc|bác sĩ|phẫu thuật|vinmec|bệnh viện|phòng khám|chuyên khoa"
    r"|nhịn ăn|giấy tờ|bảo hiểm|bhyt|đặt lịch|lịch hẹn|hẹn khám"
    r"|triệu chứng|chẩn đoán|điều trị|tái khám|kết quả|hồ sơ"
    r"|sản|nhi|tim|gan|thận|phổi|não|ung thư|tiểu đường|huyết áp"
    r"|vaccine|tiêm|covid|flu|cúm|sốt|ho|đau đầu|đau bụng"
    # Thêm: từ khoá địa điểm / tìm cơ sở
    r"|ở đâu|gần nhất|địa chỉ|đường đi|bản đồ|tỉnh|thành phố"
    r"|hà nội|hồ chí minh|đà nẵng|hải phòng|nha trang|hạ long|phú quốc"
    r"|hưng yên|thanh hóa|đặt xe|đi lại|cơ sở|chi nhánh|hotline"
    r"|myvinmec|app|đặt online|booking)",
    re.IGNORECASE,
)

_OFFTOPIC_PATTERNS = [
    r"\b(thời tiết|bóng đá|cổ phiếu|crypto|bitcoin|nấu ăn|công thức|du lịch"
    r"|phim|nhạc|game|code|lập trình|python|javascript|toán học"
    r"|lịch sử|địa lý|tiếng anh|dịch thuật)\b",
]
_OFFTOPIC_RE = re.compile("|".join(_OFFTOPIC_PATTERNS), re.IGNORECASE)

_OFFTOPIC_MSG = (
    "Xin lỗi, tôi chỉ có thể hỗ trợ về **chuẩn bị khám tại Vinmec** — "
    "như nhịn ăn, giấy tờ cần mang, đặt lịch, tìm cơ sở gần nhất, hay thắc mắc về chuyên khoa.\n\n"
    "Bạn có muốn tôi giúp chuẩn bị cho buổi khám không?"
)

# ── 4. PII patterns ───────────────────────────────────────────────────────────
_PII_PATTERNS = [
    r"\b\d{9,12}\b",
    r"\b(0[35789]\d{8})\b",
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
]
_PII_RE = re.compile("|".join(_PII_PATTERNS))

_PII_MSG = (
    "⚠️ **Lưu ý bảo mật:** Vui lòng không chia sẻ số CMND/CCCD, "
    "số điện thoại, email, hay thông tin cá nhân nhạy cảm trong cuộc trò chuyện này.\n\n"
)


# ── Public API ─────────────────────────────────────────────────────────────────
def check(text: str) -> GuardOutcome:
    if not text or not text.strip():
        return GuardOutcome(GuardResult.PASS)

    if len(text) > MAX_INPUT_CHARS:
        return GuardOutcome(
            GuardResult.TOO_LONG,
            f"Câu hỏi quá dài (tối đa {MAX_INPUT_CHARS} ký tự). Vui lòng rút gọn và thử lại."
        )

    text_lower = text.lower()

    if _HARD_BLOCK_RE.search(text_lower):
        return GuardOutcome(GuardResult.BLOCK, _HARD_BLOCK_MSG)

    if _EMERGENCY_RE.search(text_lower):
        return GuardOutcome(GuardResult.EMERGENCY, _EMERGENCY_MSG)

    if not _MEDICAL_KEYWORDS.search(text_lower) and _OFFTOPIC_RE.search(text_lower):
        return GuardOutcome(GuardResult.OFF_TOPIC, _OFFTOPIC_MSG)

    if _PII_RE.search(text):
        return GuardOutcome(GuardResult.PII_WARN, _PII_MSG)

    return GuardOutcome(GuardResult.PASS)


def is_blocked(outcome: GuardOutcome) -> bool:
    return outcome.result in (
        GuardResult.BLOCK,
        GuardResult.EMERGENCY,
        GuardResult.OFF_TOPIC,
        GuardResult.TOO_LONG,
    )
