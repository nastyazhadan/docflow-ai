from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Mapping, Optional


_PBKDF2_ITERATIONS = 310_000


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("utf-8"))


def hash_password(password: str) -> str:
    """
    Хэш пароля без внешних зависимостей (pbkdf2_hmac sha256).
    Формат: pbkdf2_sha256$<iterations>$<salt_b64url>$<hash_b64url>
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string")
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(dk)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algo, iterations_s, salt_s, hash_s = encoded_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = _b64url_decode(salt_s)
        expected = _b64url_decode(hash_s)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _secret_key() -> bytes:
    # Для тестовой/локальной версии: если ключ не задан — используем дефолт,
    # но это НЕ безопасно для production.
    return os.getenv("AUTH_SECRET_KEY", "dev-secret-key-change-me").encode("utf-8")


def create_access_token(payload: Mapping[str, Any], *, expires_in_seconds: int = 7 * 24 * 3600) -> str:
    """
    Минимальный HMAC-подписанный токен (JWT-подобный, но без зависимости).
    Формат: <payload_b64url>.<sig_b64url>
    payload содержит exp (unix seconds).
    """
    now = int(time.time())
    data: Dict[str, Any] = dict(payload)
    data["exp"] = now + int(expires_in_seconds)
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload_b64 = _b64url_encode(raw)
    sig = hmac.new(_secret_key(), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Проверяет подпись и exp. Возвращает payload.
    """
    if not token or "." not in token:
        raise ValueError("Invalid token format")
    payload_b64, sig_b64 = token.split(".", 1)
    expected_sig = hmac.new(_secret_key(), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    got_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, got_sig):
        raise ValueError("Invalid token signature")
    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    exp = payload.get("exp")
    if exp is None or int(exp) < int(time.time()):
        raise ValueError("Token expired")
    return payload


