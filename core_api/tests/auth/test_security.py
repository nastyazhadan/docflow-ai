from __future__ import annotations

from core_api.app.auth.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_and_verify_password_roundtrip() -> None:
    encoded = hash_password("super-secret")
    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("super-secret", encoded) is True
    assert verify_password("wrong", encoded) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token({"sub": "user-1", "tenant_id": "t-1"}, expires_in_seconds=60)
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "t-1"
    assert "exp" in payload


