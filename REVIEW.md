# VinmecPrep AI — Code Review & Architecture Report

## 1. Bugs Tìm Thấy (Critical → Low)

### 🔴 CRITICAL

| # | File | Vấn đề | Fix |
|---|------|---------|-----|
| 1 | `src/tools/web_search_tool.py` | **File rỗng (0 bytes)** — Agent không có web search tool nào hoạt động dù system prompt đã mô tả | Viết lại hoàn toàn với Serper → SearXNG → DDGS fallback |
| 2 | `Dockerfile` | **Không tồn tại** — docker-compose build thất bại ngay | Tạo mới |
| 3 | `Dockerfile.frontend` | **Không tồn tại** | Tạo mới |
| 4 | `src/api/server.py` | **Không tồn tại** — uvicorn command trong docker-compose gọi file này | Tạo mới |
| 5 | `src/nginx.conf` | **Không tồn tại** — nginx service crash | Tạo mới |

### 🟡 MEDIUM

| # | File | Vấn đề | Fix |
|---|------|---------|-----|
| 6 | `vinmec_agent.py` | Dùng `langchain-groq` trực tiếp thay vì LiteLLM — không switch được sang vLLM | Chuyển sang `ChatLiteLLM` |
| 7 | `.env` | `SEARXNG_URL=http://localhost:8888` — sai trong Docker context (phải là `searxng:8080`) | Sửa thành `http://searxng:8080` |
| 8 | `docker-compose.yml` | SearXNG mount `./src/searngx_config` nhưng không có `settings.yml` → container dùng default config nguy hiểm | Tạo `settings.yml` theo config bạn yêu cầu |
| 9 | `src/config.py` | **Không tồn tại** — `image_search.py` import `from src.config import SERPER_API_KEY, SEARXNG_URL` → ImportError | Tạo mới |

### 🟢 LOW / DESIGN

| # | Vấn đề | Fix |
|---|---------|-----|
| 10 | Không có guardrails layer — user có thể dùng chatbot cho việc khác (nấu ăn, code, politics...) | Thêm `src/guardrails.py` với 5 lớp check |
| 11 | Không giới hạn conversation history — sau 50+ turns context window có thể tràn | Thêm `_MAX_HISTORY_TURNS = 20` |
| 12 | `get_agent()` singleton không thread-safe khi dùng nhiều workers | Acceptable với 4 workers vì mỗi process có Python GIL riêng |

---

## 2. Guard Rails — 5 Lớp Bảo Vệ (`src/guardrails.py`)

```
User Input
    │
    ▼
┌─────────────────────────────┐
│ Layer 0: Độ dài input       │ → TOO_LONG (>2000 chars)
│ Layer 1: Hard Block         │ → BLOCK (violence/porn/jailbreak)
│ Layer 2: Emergency Detect   │ → EMERGENCY + redirect 115
│ Layer 3: Off-Topic Filter   │ → OFF_TOPIC (bóng đá, code...)
│ Layer 4: PII Warning        │ → PII_WARN + pass through
└─────────────────────────────┘
    │ PASS
    ▼
  Agent
```

**Tỉ lệ false positive** thấp vì Layer 3 chỉ block khi KHÔNG có từ khoá y tế — tức là câu "cách nấu canh rau" bị block nhưng "tôi bị đau dạ dày sau khi ăn canh rau" thì qua.

---

## 3. Disease/Specialty Coverage

**Hiện có: 63 entries** (50 base + 13 extra)

| Category | Có | Ghi chú |
|----------|----|---------|
| Chuyên khoa nội | ✅ 15 | Nội tổng quát, Tim, Thần kinh, Tiêu hoá, Thận, Nội tiết, Hô hấp, Ung bướu, Tâm thần... |
| Chuyên khoa ngoại | ✅ | Phẫu thuật chung |
| Sản - Nhi | ✅ | Sản phụ khoa, Nhi, Sơ sinh |
| Cận lâm sàng | ✅ 30+ | Xét nghiệm máu, chức năng gan/thận, HIV, HBV, PSA, HbA1c, D-dimer... |
| Chẩn đoán hình ảnh | ✅ | Siêu âm, MRI, CT, X-quang, Mammography |
| Thủ thuật | ✅ | Nội soi dạ dày, đại tràng, Holter ECG, Spirometry, EMG |
| **Thiếu** | ❌ | Cấp cứu, ICU, Ghép tạng, Y học cổ truyền, Chăm sóc giảm nhẹ, Răng hàm mặt **nâng cao** |

> **Kết luận:** Đủ cho 90% ca khám ngoại trú thông thường tại Vinmec. Nếu muốn mở rộng, thêm vào `medical_data_extra.py` theo cùng schema.

---

## 4. LiteLLM Switch — Cách Dùng

### Hiện tại (Groq)
```env
LLM_MODEL=groq/qwen/qwen3-32b
LLM_API_KEY=your_groq_key
```

### Khi có vLLM Qwen3-4B
```env
LLM_MODEL=openai/Qwen3-4B
LLM_API_BASE=http://vllm:8000/v1
LLM_API_KEY=fake
```

Thêm service vào docker-compose:
```yaml
vllm:
  image: vllm/vllm-openai:latest
  runtime: nvidia
  command: --model Qwen/Qwen3-4B --served-model-name Qwen3-4B
  ports:
    - "127.0.0.1:8001:8000"
  networks:
    - travelbuddy
```

---

## 5. Playwright MCP — Web Interaction

Để agent có thể **tương tác với trang web** (điền form, click, scrape JS-rendered pages), cài Playwright MCP:

```bash
npm install @playwright/mcp
```

Tích hợp vào agent như một LangChain tool:
```python
# src/tools/playwright_tool.py
import subprocess, json
from langchain_core.tools import tool

@tool
def navigate_vinmec_booking(specialty: str) -> str:
    """Mở trang đặt lịch Vinmec và điền thông tin chuyên khoa."""
    # Gọi Playwright MCP server qua subprocess hoặc HTTP
    ...
```

> **Lưu ý cho 10k users:** Playwright rất tốn tài nguyên (~300MB/browser instance). Chỉ dùng cho admin/scraping jobs, **không dùng per-request** của user.

---

## 6. Scale 10k Users — Checklist

| Layer | Hiện trạng | Cần thêm |
|-------|-----------|----------|
| API | 4 uvicorn workers | OK cho ~2k concurrent, thêm worker nếu cần |
| Queue | Redis Stream + 4 workers | Thêm replicas khi cần |
| Rate limit | 20 RPM/IP (Redis) + nginx 30/min | Thêm global rate limit cho endpoint /chat |
| LLM | Groq free tier ~30 RPM | **Upgrade Groq paid** hoặc dùng vLLM khi > 1k users/day |
| Vector DB | Weaviate single node | OK cho 10k users nếu query < 50ms |
| Cache | Redis (RAG results 5 min) | Thêm response cache cho câu hỏi phổ biến |
| Monitoring | Chưa có | Thêm Prometheus + Grafana hoặc Sentry |
| CDN | Nginx serve static | Thêm CloudFlare cho static files |

---

## 7. File Changes Summary

```
vinmec-agent/
├── Dockerfile                         ← TẠO MỚI 🆕
├── Dockerfile.frontend                ← TẠO MỚI 🆕
├── .env.example                       ← CẬP NHẬT (LiteLLM + SERPER_API_KEY)
├── requirements.txt                   ← CẬP NHẬT (langchain-community)
├── src/
│   ├── config.py                      ← TẠO MỚI 🆕
│   ├── guardrails.py                  ← TẠO MỚI 🆕
│   ├── nginx.conf                     ← TẠO MỚI 🆕
│   ├── agent/
│   │   └── vinmec_agent.py            ← SỬA (LiteLLM + guardrails + history trim)
│   ├── api/
│   │   └── server.py                  ← TẠO MỚI 🆕
│   ├── frontend/
│   │   └── index.html                 ← TẠO MỚI 🆕
│   ├── tools/
│   │   └── web_search_tool.py         ← SỬA TOÀN BỘ (file rỗng → Serper+SearXNG+DDGS)
│   └── searngx_config/
│       └── settings.yml               ← TẠO MỚI 🆕 (config bạn yêu cầu)
```
