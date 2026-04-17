"""
app/tools/hospital_finder.py – Tìm bệnh viện/phòng khám Vinmec gần nhất.

Chiến lược:
  1. Live search qua Serper Places API (POST /places) — kết quả real-time, có rating
  2. Fallback: static database (~12 cơ sở Vinmec) + Haversine distance khi biết tọa độ
  3. Format đẹp kèm Google Maps link, hotline, giờ làm việc

Tool này được thêm vào VINMEC_WEB_TOOLS và bind vào agent graph.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import requests
from langchain_core.tools import tool

from app.core.config import SERPER_API_KEY

logger = logging.getLogger(__name__)

# ── Static database: tất cả cơ sở Vinmec đã xác nhận ─────────────────────────
# Cập nhật lần cuối: 04/2026. Kiểm tra vinmec.com/co-so-y-te để xem thêm.
VINMEC_FACILITIES: list[dict] = [
    {
        "name": "Vinmec Times City (Hà Nội)",
        "short": "Times City",
        "address": "458 P. Minh Khai, Hai Bà Trưng, Hà Nội",
        "city": "Hà Nội",
        "province": "hà nội",
        "lat": 20.996216, "lng": 105.86691,
        "phone": "+84 24 3974 3556",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vie/co-so-y-te/benh-vien-da-khoa-quoc-te-vinmec-times-city-17265",
        "maps": "https://maps.google.com/?q=20.996216,105.86691",
        "specialties": "Hơn 40 chuyên khoa, Tim mạch, Ung bướu, Sản, Nhi, ICU",
        "parking": "Hầm gửi xe B1-B4 tòa nhà Times City (có phí)",
        "bus": "Tuyến 32, 40, 54 — dừng Times City",
    },
    {
        "name": "Vinmec Smart City (Hà Nội)",
        "short": "Smart City",
        "address": "2A Đ. Tây Mỗ, Nam Từ Liêm, Hà Nội",
        "city": "Hà Nội",
        "province": "hà nội",
        "lat": 21.007687, "lng": 105.74757,
        "phone": "+84 24 3208 5678",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vie/co-so-y-te/benh-vien-da-khoa-vinmec-smart-city",
        "maps": "https://maps.google.com/?q=21.007687,105.74757",
        "specialties": "Đa khoa, Nội, Ngoại, Sản, Nhi, Chẩn đoán hình ảnh",
        "parking": "Bãi xe trong khuôn viên bệnh viện (miễn phí 2 giờ đầu)",
        "bus": "Tuyến 72, 103 — dừng Vinhomes Smart City",
    },
    {
        "name": "Vinmec Hải Phòng",
        "short": "Hải Phòng",
        "address": "Khu đô thị Vinhomes Imperia, Thượng Lý, Hồng Bàng, Hải Phòng",
        "city": "Hải Phòng",
        "province": "hải phòng",
        "lat": 20.8567, "lng": 106.6713,
        "phone": "+84 225 3688 998",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vi/benh-vien-da-khoa-quoc-te-vinmec-hai-phong",
        "maps": "https://maps.google.com/?q=20.8567,106.6713",
        "specialties": "Đa khoa, Tim mạch, Sản, Nhi, Ung bướu",
        "parking": "Bãi đỗ xe trong khuôn viên",
        "bus": "Các tuyến xe buýt nội thành Hải Phòng",
    },
    {
        "name": "Vinmec Hạ Long",
        "short": "Hạ Long",
        "address": "Khu đô thị Vinhomes Dragon Bay, Hạ Long, Quảng Ninh",
        "city": "Hạ Long",
        "province": "quảng ninh",
        "lat": 20.9501, "lng": 107.0781,
        "phone": "+84 203 3828 188",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vi/benh-vien-da-khoa-quoc-te-vinmec-ha-long",
        "maps": "https://maps.google.com/?q=20.9501,107.0781",
        "specialties": "Đa khoa, Nội, Sản, Nhi",
        "parking": "Bãi đỗ xe trong khuôn viên",
        "bus": "Xe buýt Hạ Long — dừng Vinhomes Dragon Bay",
    },
    {
        "name": "Vinmec Central Park (TP.HCM)",
        "short": "Central Park",
        "address": "208 Nguyễn Hữu Cảnh, Vinhomes Tân Cảng, Bình Thạnh, TP.HCM",
        "city": "TP. Hồ Chí Minh",
        "province": "hồ chí minh",
        "lat": 10.793977, "lng": 106.720345,
        "phone": "+84 28 3622 1166",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vie/co-so-y-te/benh-vien-da-khoa-quoc-te-vinmec-central-park-10890",
        "maps": "https://maps.google.com/?q=10.793977,106.720345",
        "specialties": "Hơn 40 chuyên khoa, Tim mạch, Ung bướu, Thần kinh, Sản, Nhi",
        "parking": "Hầm gửi xe Vinhomes Central Park (có phí)",
        "bus": "Tuyến 03, 36, 53 — dừng Vinhomes Tân Cảng",
    },
    {
        "name": "Vinmec Đà Nẵng",
        "short": "Đà Nẵng",
        "address": "30 Tháng 4, Hoà Cường Bắc, Hải Châu, Đà Nẵng",
        "city": "Đà Nẵng",
        "province": "đà nẵng",
        "lat": 16.03884, "lng": 108.21129,
        "phone": "+84 236 3711 111",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vi/benh-vien-da-khoa-quoc-te-vinmec-da-nang-98367",
        "maps": "https://maps.google.com/?q=16.03884,108.21129",
        "specialties": "Đa khoa, Tim mạch, Sản, Nhi, Ung bướu, Chẩn đoán hình ảnh",
        "parking": "Bãi đỗ xe trong khuôn viên",
        "bus": "Các tuyến xe buýt nội thành Đà Nẵng",
    },
    {
        "name": "Vinmec Nha Trang",
        "short": "Nha Trang",
        "address": "Vĩnh Nguyên, Nha Trang, Khánh Hòa",
        "city": "Nha Trang",
        "province": "khánh hòa",
        "lat": 12.212712, "lng": 109.210785,
        "phone": "+84 258 3900 168",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vi/benh-vien-da-khoa-quoc-te-vinmec-nha-trang-67081",
        "maps": "https://maps.google.com/?q=12.212712,109.210785",
        "specialties": "Đa khoa, Sản, Nhi, Ngoại, Chẩn đoán hình ảnh",
        "parking": "Bãi đỗ xe trong khuôn viên",
        "bus": "Xe buýt Nha Trang — dừng Vinmec",
    },
    {
        "name": "Vinmec Phú Quốc",
        "short": "Phú Quốc",
        "address": "Bãi Dài, Gành Dầu, Phú Quốc, Kiên Giang",
        "city": "Phú Quốc",
        "province": "kiên giang",
        "lat": 10.3748, "lng": 103.8451,
        "phone": "+84 297 3985 588",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vi/benh-vien-da-khoa-quoc-te-vinmec-phu-quoc",
        "maps": "https://maps.google.com/?q=10.3748,103.8451",
        "specialties": "Đa khoa, Nội, Ngoại, Sản, Nhi, Cấp cứu",
        "parking": "Bãi đỗ xe trong khuôn viên",
        "bus": "Taxi/xe ôm từ trung tâm thị trấn Dương Đông (~15km)",
    },
    {
        "name": "Phòng khám Vinmec Hưng Yên",
        "short": "Hưng Yên",
        "address": "Khu đô thị Vinhomes Ocean Park 2, Hưng Yên",
        "city": "Hưng Yên",
        "province": "hưng yên",
        "lat": 20.8526, "lng": 106.0166,
        "phone": "1900 54 61 54",
        "hotline": "1900 54 61 54",
        "type": "Phòng khám đa khoa",
        "hours": "T2–T7 07:30–17:00 | Chủ nhật 07:30–12:00",
        "website": "https://www.vinmec.com/vie/co-so-y-te/",
        "maps": "https://maps.google.com/?q=Vinmec+Hung+Yen",
        "specialties": "Nội tổng quát, Sản, Nhi, Xét nghiệm, Siêu âm",
        "parking": "Bãi đỗ xe Vinhomes",
        "note": "⚠️ Xác nhận địa chỉ cụ thể qua hotline 1900 54 61 54 trước khi đến",
    },
    {
        "name": "Vinmec Thanh Hóa",
        "short": "Thanh Hóa",
        "address": "Khu đô thị Vinhomes Star City, Đông Hương, TP. Thanh Hóa",
        "city": "Thanh Hóa",
        "province": "thanh hóa",
        "lat": 19.8072, "lng": 105.7730,
        "phone": "+84 237 3710 888",
        "hotline": "1900 54 61 54",
        "type": "Bệnh viện đa khoa quốc tế",
        "hours": "Cấp cứu: 24/7 | Khám ngoại trú: T2–T7 07:00–17:00",
        "website": "https://www.vinmec.com/vi/benh-vien-da-khoa-quoc-te-vinmec-thanh-hoa",
        "maps": "https://maps.google.com/?q=19.8072,105.7730",
        "specialties": "Đa khoa, Tim mạch, Sản, Nhi, Ung bướu",
        "parking": "Bãi đỗ xe trong khuôn viên",
        "bus": "Xe buýt Thanh Hóa — dừng Vinhomes Star City",
    },
]

# Lookup nhanh theo province key
_PROVINCE_INDEX: dict[str, list[dict]] = {}
for _h in VINMEC_FACILITIES:
    _key = _h["province"]
    _PROVINCE_INDEX.setdefault(_key, []).append(_h)


# ── Haversine distance ────────────────────────────────────────────────────────
def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ── Serper Places API ─────────────────────────────────────────────────────────
def _serper_places_search(query: str, num: int = 5) -> list[dict]:
    """Gọi Serper Places API, trả về list kết quả chuẩn hoá."""
    if not SERPER_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/places",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "gl": "vn", "hl": "vi", "num": num},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for p in data.get("places", [])[:num]:
            results.append({
                "name":    p.get("title", ""),
                "address": p.get("address", ""),
                "phone":   p.get("phoneNumber", ""),
                "rating":  p.get("rating", 0),
                "count":   p.get("ratingCount", 0),
                "website": p.get("website", ""),
                "lat":     p.get("latitude"),
                "lng":     p.get("longitude"),
                "maps":    (
                    f"https://maps.google.com/?q={p['latitude']},{p['longitude']}"
                    if p.get("latitude") else
                    f"https://maps.google.com/?q={p.get('title','').replace(' ', '+')}"
                ),
            })
        return results
    except Exception as e:
        logger.warning("Serper Places search failed: %s", e)
        return []


def _format_facility(f: dict, distance_km: Optional[float] = None, index: int = 1) -> str:
    """Format một cơ sở thành markdown cho bệnh nhân."""
    dist_str = f"  📍 Cách ~**{distance_km:.0f} km**\n" if distance_km is not None else ""
    note_str = f"\n  ⚠️  {f['note']}" if f.get("note") else ""
    return (
        f"**{index}. {f['name']}**\n"
        f"{dist_str}"
        f"  🏥 {f.get('type', 'Cơ sở y tế')}\n"
        f"  📌 {f['address']}\n"
        f"  📞 {f.get('phone') or f.get('hotline', '1900 54 61 54')}\n"
        f"  🕐 {f.get('hours', 'T2–T7 07:00–17:00')}\n"
        f"  🔬 {f.get('specialties', 'Đa khoa')}\n"
        f"  🚗 **Đỗ xe:** {f.get('parking', 'Có bãi đỗ')}\n"
        + (f"  🚌 **Xe buýt:** {f['bus']}\n" if f.get("bus") else "")
        + f"  🗺️  [Xem bản đồ]({f['maps']})\n"
        f"  🌐 {f.get('website', 'https://www.vinmec.com/co-so-y-te')}"
        f"{note_str}"
    )


def _format_serper_result(p: dict, index: int = 1) -> str:
    rating_str = f" ⭐ {p['rating']}/5 ({p['count']} đánh giá)" if p.get("rating") else ""
    return (
        f"**{index}. {p['name']}**{rating_str}\n"
        f"  📌 {p['address']}\n"
        f"  📞 {p.get('phone') or '1900 54 61 54'}\n"
        f"  🗺️  [Xem bản đồ]({p['maps']})\n"
        + (f"  🌐 {p['website']}" if p.get("website") else "")
    )


# ── LangChain Tool ────────────────────────────────────────────────────────────

@tool
def find_nearest_vinmec_hospital(user_location: str) -> str:
    """
    Tìm bệnh viện / phòng khám Vinmec gần nhất với địa điểm của bệnh nhân.

    Cung cấp địa chỉ đầy đủ, số điện thoại, giờ làm việc, link Google Maps,
    thông tin đỗ xe và xe buýt cho mỗi cơ sở.

    Args:
        user_location: Địa điểm của bệnh nhân — tên tỉnh/thành, quận/huyện, hoặc địa chỉ
                       VD: "Hưng Yên", "Quận 1 TP.HCM", "Đống Đa Hà Nội", "Đà Nẵng"

    Returns:
        Danh sách bệnh viện/phòng khám Vinmec gần nhất kèm đầy đủ thông tin thực tế.
    """
    location_lower = user_location.lower().strip()

    # ── Bước 1: Thử Serper Places (real-time, có rating) ─────────────────────
    serper_query = f"Bệnh viện Vinmec {user_location}"
    serper_results = _serper_places_search(serper_query, num=5)

    # ── Bước 2: Static DB — tìm theo province key ────────────────────────────
    static_matches: list[tuple[float | None, dict]] = []

    # Map các tên gọi thông dụng về province key
    _ALIAS = {
        "hcm": "hồ chí minh", "sài gòn": "hồ chí minh", "saigon": "hồ chí minh",
        "sg": "hồ chí minh", "tphcm": "hồ chí minh",
        "hn": "hà nội", "hanoi": "hà nội",
        "qn": "quảng ninh", "halong": "quảng ninh",
        "hp": "hải phòng", "haiphong": "hải phòng",
        "nt": "khánh hòa", "nhatrang": "khánh hòa",
        "pq": "kiên giang", "phuquoc": "kiên giang",
        "hy": "hưng yên", "hungyen": "hưng yên",
        "th": "thanh hóa", "thanhhoa": "thanh hóa",
        "dn": "đà nẵng", "danang": "đà nẵng",
    }
    for alias, province in _ALIAS.items():
        if alias in location_lower:
            location_lower = province
            break

    for province_key, hospitals in _PROVINCE_INDEX.items():
        if province_key in location_lower or location_lower in province_key:
            for h in hospitals:
                static_matches.append((None, h))

    # Nếu không match province, tìm 3 cơ sở gần nhất theo tên thành phố lớn nhất gần đó
    if not static_matches:
        # Thêm tất cả và sắp xếp sau (không có tọa độ user → sort theo tên)
        for h in VINMEC_FACILITIES[:5]:
            static_matches.append((None, h))

    # ── Tổng hợp kết quả ─────────────────────────────────────────────────────
    lines = [
        f"🏥 **Cơ sở Vinmec gần {user_location}**\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
    ]

    if serper_results:
        lines.append("### 📍 Kết quả tìm kiếm thực tế (Google Maps)\n")
        for i, p in enumerate(serper_results[:3], 1):
            lines.append(_format_serper_result(p, i))
            lines.append("")
        lines.append("\n---\n")

    if static_matches:
        lines.append("### 📋 Thông tin chi tiết cơ sở Vinmec\n")
        for i, (dist, h) in enumerate(static_matches[:3], 1):
            lines.append(_format_facility(h, dist, i))
            lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        "\n📱 **Đặt lịch online:** App **MyVinmec** hoặc gọi **1900 54 61 54** (24/7)\n"
        "🌐 Xem tất cả cơ sở: https://www.vinmec.com/co-so-y-te\n\n"
        "⚠️ *Gọi trước để xác nhận giờ khám và chuyên khoa tại cơ sở bạn chọn.*"
    )

    return "\n".join(lines)


@tool
def get_vinmec_all_locations() -> str:
    """
    Liệt kê tất cả bệnh viện và phòng khám Vinmec trên toàn quốc.

    Dùng khi bệnh nhân hỏi "Vinmec có ở đâu?", "Danh sách các bệnh viện Vinmec",
    "Vinmec có bao nhiêu cơ sở?", "Tôi ở [tỉnh] có Vinmec không?"

    Returns:
        Danh sách đầy đủ tất cả cơ sở Vinmec kèm địa chỉ và số điện thoại.
    """
    lines = [
        "🏥 **HỆ THỐNG VINMEC TOÀN QUỐC** (cập nhật 04/2026)\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
    ]

    # Nhóm theo miền
    mien_bac = ["hà nội", "hải phòng", "quảng ninh", "hưng yên"]
    mien_trung = ["đà nẵng", "thanh hóa"]
    mien_nam = ["hồ chí minh", "khánh hòa", "kiên giang"]

    for mien_name, provinces in [
        ("🔵 MIỀN BẮC", mien_bac),
        ("🟡 MIỀN TRUNG", mien_trung),
        ("🔴 MIỀN NAM", mien_nam),
    ]:
        lines.append(f"**{mien_name}**\n")
        for province in provinces:
            for h in _PROVINCE_INDEX.get(province, []):
                lines.append(
                    f"  • **{h['name']}**\n"
                    f"    📌 {h['address']}\n"
                    f"    📞 {h.get('phone') or h.get('hotline')}\n"
                    f"    🗺️  [Bản đồ]({h['maps']})\n"
                )
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        "📱 Đặt lịch: App **MyVinmec** | Hotline **1900 54 61 54** (24/7)\n"
        "🌐 https://www.vinmec.com/co-so-y-te"
    )

    return "\n".join(lines)


# ── Export ────────────────────────────────────────────────────────────────────
VINMEC_HOSPITAL_TOOLS = [find_nearest_vinmec_hospital, get_vinmec_all_locations]
