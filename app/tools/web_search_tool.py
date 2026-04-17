"""
app/tools/web_search_tool.py – Web search tool cho Vinmec agent.

Priority: Serper API → SearXNG → DuckDuckGo (DDGS)
Kèm fetch nội dung đầy đủ từ URL (readability + markdownify).
"""
from __future__ import annotations

import logging
import time
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal, Optional
from urllib.parse import urlparse

import requests
from langchain_core.tools import tool

from app.core.config import SERPER_API_KEY, SEARXNG_URL, WEB_SEARCH_TOP_K

logger = logging.getLogger(__name__)

ExtractMode = Literal["markdown", "text"]

# ── Fetch helpers (từ searxng.py của bạn) ────────────────────────────────────

_FETCH_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300
_MAX_CHARS  = 40_000   # Đủ cho agent, không quá lớn
_MAX_BYTES  = 1_000_000
_TIMEOUT    = 20
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _fetch_url(url: str) -> dict:
    """Fetch + extract markdown content từ một URL."""
    key = _cache_key(url)
    entry = _FETCH_CACHE.get(key)
    if entry and time.time() < entry[0]:
        return {**entry[1], "cached": True}

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")

    session = requests.Session()
    session.max_redirects = 3
    resp = session.get(
        url,
        timeout=_TIMEOUT,
        headers={
            "Accept": "text/html,*/*;q=0.8",
            "User-Agent": _USER_AGENT,
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        },
        stream=True,
    )

    chunks, total = [], 0
    for chunk in resp.iter_content(8192):
        chunks.append(chunk)
        total += len(chunk)
        if total >= _MAX_BYTES:
            break
    body = b"".join(chunks).decode("utf-8", errors="replace")

    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.reason}")

    ct = resp.headers.get("content-type", "")
    text, title = body, None

    if "text/html" in ct:
        try:
            from readability import Document
            from markdownify import markdownify as md
            doc   = Document(body)
            title = doc.title()
            text  = md(doc.summary(), heading_style="ATX").strip()
        except Exception:
            pass

    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]

    payload = {"url": url, "title": title, "text": text, "length": len(text)}
    _FETCH_CACHE[key] = (time.time() + _CACHE_TTL, payload)
    return payload


# ── Search providers ──────────────────────────────────────────────────────────

def _search_serper(query: str, k: int) -> tuple[list[dict], str | None]:
    """Serper.dev – Google Search API (ưu tiên 1)."""
    if not SERPER_API_KEY:
        return [], "SERPER_API_KEY chưa cấu hình"
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": k + 3, "gl": "vn", "hl": "vi"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("organic", [])[:k]:
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("link",  ""),
                "snippet": item.get("snippet", ""),
            })
        return results, None
    except Exception as e:
        return [], f"Serper lỗi: {e}"


def _search_searxng(query: str, k: int) -> tuple[list[dict], str | None]:
    """SearXNG local instance (ưu tiên 2)."""
    try:
        resp = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json", "categories": "general"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", [])[:k]:
            results.append({
                "title":   item.get("title",   ""),
                "url":     item.get("url",     ""),
                "snippet": item.get("content", ""),
            })
        return results, None
    except Exception as e:
        return [], f"SearXNG lỗi: {e}"


def _search_ddgs(query: str, k: int) -> tuple[list[dict], str | None]:
    """DuckDuckGo fallback (ưu tiên 3)."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=k + 3, region="vn-vi"))
        results = []
        for item in raw[:k]:
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("href",  ""),
                "snippet": item.get("body",  ""),
            })
        return results, None
    except Exception as e:
        return [], f"DDGS lỗi: {e}"


def _multi_search(query: str, k: int) -> list[dict]:
    """Thử Serper → SearXNG → DDGS, dừng khi có kết quả."""
    errors = []
    for fn in (_search_serper, _search_searxng, _search_ddgs):
        results, err = fn(query, k)
        if results:
            logger.debug("Search provider %s succeeded for: %s", fn.__name__, query)
            return results
        if err:
            errors.append(err)
    logger.warning("All search providers failed: %s", " | ".join(errors))
    return []


# ── LangChain tools ───────────────────────────────────────────────────────────

@tool
def web_search_medical(query: str, top_k: int = 5) -> str:
    """
    Tìm kiếm thông tin y tế / Vinmec trên web khi RAG không có đủ thông tin.

    Dùng khi:
    - RAG trả về "Không tìm thấy" hoặc kết quả quá chung chung
    - Bệnh nhân hỏi về thủ thuật / bệnh lý hiếm gặp
    - Cần thông tin hướng dẫn cập nhật nhất từ vinmec.com

    Args:
        query: Từ khoá tìm kiếm (nên kèm "Vinmec" hoặc "chuẩn bị khám" để tăng độ chính xác)
               VD: "Vinmec nội soi dạ dày cần chuẩn bị gì"
        top_k: Số kết quả (mặc định 5, tối đa 8)

    Returns:
        Kết quả tìm kiếm dạng markdown với tiêu đề, URL và snippet.
    """
    top_k = max(1, min(int(top_k), 8))

    # Tự động thêm context Vinmec nếu chưa có
    if "vinmec" not in query.lower() and "khám" not in query.lower():
        query = f"Vinmec {query}"

    results = _multi_search(query, top_k)
    if not results:
        return (
            "Không tìm thấy kết quả phù hợp trên web. "
            "Vui lòng gọi 1900 54 61 54 để được hỗ trợ trực tiếp."
        )

    lines = [f"**Kết quả tìm kiếm cho:** _{query}_\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**[{i}] {r['title']}**")
        lines.append(f"🔗 {r['url']}")
        if r["snippet"]:
            lines.append(f"_{r['snippet'][:300]}_")
        lines.append("")

    return "\n".join(lines)


@tool
def fetch_webpage_content(url: str) -> str:
    """
    Lấy nội dung đầy đủ từ một trang web (sau khi đã có URL từ web_search_medical).

    Dùng khi:
    - Snippet từ web_search_medical quá ngắn, cần chi tiết hơn
    - Muốn đọc nội dung đầy đủ từ vinmec.com hoặc nguồn y tế uy tín

    Args:
        url: URL cần fetch (phải bắt đầu bằng http:// hoặc https://)

    Returns:
        Nội dung trang web dạng markdown, tối đa 40,000 ký tự.
    """
    # Chỉ cho phép fetch domain y tế / uy tín để tránh abuse
    ALLOWED_DOMAINS = {
        "vinmec.com", "medlatec.vn", "benhvien108.vn",
        "suckhoedoisong.vn", "moh.gov.vn", "who.int",
        "pubmed.ncbi.nlm.nih.gov", "healthline.com", "webmd.com",
        "mayoclinic.org", "nih.gov", "cdc.gov",
    }
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().removeprefix("www.")
        if not any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS):
            return (
                f"⚠️ Domain `{domain}` không nằm trong danh sách được phép. "
                "Chỉ fetch các trang y tế uy tín (vinmec.com, moh.gov.vn, ...)."
            )
        result = _fetch_url(url)
        title = result.get("title") or "Không có tiêu đề"
        text  = result.get("text", "")
        return f"# {title}\n\n🔗 {url}\n\n{text}"
    except Exception as e:
        logger.error("fetch_webpage_content error for %s: %s", url, e)
        return f"Không thể tải nội dung từ {url}: {e}"


# ── Export ────────────────────────────────────────────────────────────────────
VINMEC_WEB_TOOLS = [web_search_medical, fetch_webpage_content]
