from __future__ import annotations

import logging
import os
from typing import Any, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


def get_core_api_base_url() -> str:
    """
    Default is http://api:8000 for Docker network; override via CORE_API_BASE_URL.
    """
    return os.getenv("CORE_API_BASE_URL", "http://api:8000").rstrip("/")


async def core_request_json(
    method: str,
    url: str,
    *,
    token: Optional[str] = None,
    json_body: Any = None,
    timeout_s: float = 60.0,
) -> Tuple[int, str, Any]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.request(method, url, headers=headers, json=json_body)

    text_body = resp.text or ""
    try:
        data = resp.json()
    except Exception:
        data = None

    return resp.status_code, text_body, data


