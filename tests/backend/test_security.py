"""Tests: security utilities — hashing, JWT, API key."""
import pytest
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    create_api_key_hash, verify_api_key,
)


def test_password_hash_and_verify():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_access_token_decode():
    token = create_access_token("user-123")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_refresh_token_decode():
    token = create_refresh_token("user-456")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_access_token_rejected_as_refresh():
    token = create_access_token("user-789")
    payload = decode_token(token)
    assert payload["type"] != "refresh"


def test_invalid_token_returns_none():
    result = decode_token("not.a.valid.jwt")
    assert result is None


def test_api_key_hash_and_verify():
    raw = "df_supersecretapikey12345"
    hashed = create_api_key_hash(raw)
    assert hashed != raw
    assert verify_api_key(raw, hashed)
    assert not verify_api_key("df_wrongkey", hashed)
