# VinmecPrep AI — Changelog v1.1.0

## Fixes so với v1.0 (vinmec-agent-fixed)

### 🔴 Critical Fixes

| # | Vấn đề | Fix |
|---|--------|-----|
| 1 | SearXNG: `FileNotFoundError: google images.py / youtube.py` | Đổi sang `use_default_settings.engines.keep_only` thay vì `disabled: true` |
| 2 | Rate limit bypass qua `X-Forwarded-For` giả | Nginx set `X-Forwarded-For = $remote_addr` (không dùng `$proxy_add_x_forwarded_for`); server.py dùng `X-Real-IP` |
| 3 | CORS `allow_origins=["*"]` | Đọc từ env var `ALLOWED_ORIGINS` — mặc định chỉ localhost |

### 🟡 Improvements

| # | Thay đổi | Chi tiết |
|---|----------|----------|
| 4 | **Tìm cơ sở Vinmec gần nhất** | Thêm `src/tools/hospital_finder.py` — 2 tools mới: `find_nearest_vinmec_hospital` + `get_vinmec_all_locations` |
| 5 | **Database 10 cơ sở Vinmec** | Times City, Smart City (HN), Hải Phòng, Hạ Long, Central Park (HCM), Đà Nẵng, Nha Trang, Phú Quốc, Hưng Yên, Thanh Hóa — kèm địa chỉ, SĐT, giờ khám, đỗ xe, xe buýt |
| 6 | **Serper Places API** | Tìm Vinmec real-time qua Google Places kèm rating |
| 7 | **ALLOWED_ORIGINS** | Thêm vào `config.py` + `.env` |
| 8 | **Sentry integration** | Thêm optional error tracking qua `SENTRY_DSN` |
| 9 | **Guardrails location keywords** | Thêm `ở đâu, gần nhất, địa chỉ, bản đồ, tỉnh/thành phố, hotline, myvinmec` vào `_MEDICAL_KEYWORDS` → không bị block khi hỏi địa điểm |
| 10 | **System prompt** | Thêm hướng dẫn khi nào dùng hospital tools |
| 11 | **.gitignore** | Thêm file `.gitignore` chuẩn (tránh commit `.env`) |
| 12 | **`.env` đầy đủ** | Tất cả biến có comment giải thích, 3 option LLM provider |

## Cấu trúc file mới

```
vinmec-production/
├── .env                          ← CẬP NHẬT (đầy đủ + ALLOWED_ORIGINS + SENTRY_DSN)
├── .env.example                  ← FILE MẪU CHUẨN DUY NHẤT
├── .gitignore                    ← MỚI
├── CHANGES.md                    ← MỚI (file này)
└── src/
    ├── config.py                 ← CẬP NHẬT (thêm ALLOWED_ORIGINS)
    ├── guardrails.py             ← CẬP NHẬT (thêm location keywords)
    ├── nginx.conf                ← FIX (X-Real-IP spoofing)
    ├── searngx_config/
    │   └── settings.yml          ← FIX (keep_only engines)
    ├── api/
    │   └── server.py             ← FIX (CORS + rate limit IP + Sentry)
    ├── agent/
    │   └── vinmec_agent.py       ← CẬP NHẬT (import hospital tools + system prompt)
    └── tools/
        └── hospital_finder.py    ← MỚI (Serper Places + static DB + 2 tools)
```

## Cách dùng hospital finder

Bệnh nhân có thể hỏi tự nhiên:
- "Tôi ở Hưng Yên, Vinmec gần nhất ở đâu?"
- "Địa chỉ Vinmec Times City là gì?"
- "Vinmec Central Park đỗ xe chỗ nào?"
- "Có bao nhiêu bệnh viện Vinmec ở Hà Nội?"
- "Đi xe buýt đến Vinmec được không?"
- "Mấy giờ Vinmec mở cửa?"

Agent tự động chọn đúng tool và trả về thông tin đầy đủ.
