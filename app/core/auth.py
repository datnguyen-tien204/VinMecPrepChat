from __future__ import annotations

import hashlib
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

public_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
trainer_api_key_header = APIKeyHeader(name="X-Trainer-Key", auto_error=False)


def require_client_key(key: Optional[str] = Security(public_api_key_header)) -> str:
    if not settings.agent_api_key:
        raise HTTPException(503, "AGENT_API_KEY chưa được cấu hình.")
    if key != settings.agent_api_key:
        raise HTTPException(401, "API key không hợp lệ.")
    return key


def require_trainer_key(key: Optional[str] = Security(trainer_api_key_header)) -> str:
    if not settings.trainer_api_key:
        raise HTTPException(503, "TRAINER_API_KEY chưa được cấu hình.")
    if key != settings.trainer_api_key:
        raise HTTPException(401, "Trainer API key không hợp lệ.")
    return key


def _resolve_client_scope(
    request: Request,
    client_key: str,
) -> str:
    raw_user_id = request.headers.get("X-User-ID", "").strip()
    api_key_fingerprint = hashlib.sha256(client_key.encode("utf-8")).hexdigest()[:16]

    if raw_user_id:
        cleaned = raw_user_id.replace("-", "").replace("_", "")
        if len(raw_user_id) > 128 or not cleaned.isalnum():
            raise HTTPException(400, "X-User-ID chỉ được gồm chữ, số, '-' hoặc '_'.")
        return f"user:{raw_user_id}:key:{api_key_fingerprint}"

    client_ip = request.headers.get("X-Real-IP") or (request.client.host if request.client else "unknown")
    return f"ip:{client_ip}:key:{api_key_fingerprint}"


def resolve_request_scopes(
    request: Request,
    client_key: str,
    session_id: Optional[str] = None,
) -> dict[str, str]:
    client_scope = _resolve_client_scope(request, client_key)
    scopes = {"client_scope": client_scope}
    if session_id:
        scopes["session_scope"] = f"session:{session_id}:subject:{client_scope}"
    return scopes


def resolve_request_identity(
    request: Request,
    client_key: str,
    session_id: Optional[str] = None,
) -> str:
    return resolve_request_scopes(request, client_key, session_id)["client_scope"]
