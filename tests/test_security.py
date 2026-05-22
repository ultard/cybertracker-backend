"""Юнит-тесты модуля безопасности (JWT, пароли)."""

from datetime import UTC, datetime, timedelta

import pytest
from app.config import get_settings
from app.core.security import (
    JWT_TYP_ACCESS,
    JWT_TYP_REFRESH,
    constant_time_equals,
    create_access_token,
    create_refresh_token,
    create_refresh_token_with_jti,
    decode_token,
    hash_password,
    is_access_token_payload,
    refresh_jti_hash,
    safe_decode_token,
    verify_password,
)
from jose import jwt


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("secret-pass")
    assert hashed != "secret-pass"
    assert verify_password("secret-pass", hashed)
    assert not verify_password("wrong", hashed)


def test_hash_password_truncates_beyond_72_bytes():
    long_password = "x" * 100
    hashed = hash_password(long_password)
    assert verify_password("x" * 72, hashed)


def test_create_access_token_decodes_with_sub_and_typ():
    token = create_access_token("42", extra={"role": "admin"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["typ"] == JWT_TYP_ACCESS
    assert payload["role"] == "admin"


def test_create_refresh_token_has_refresh_typ():
    token = create_refresh_token("7")
    payload = decode_token(token)
    assert payload["sub"] == "7"
    assert payload["typ"] == JWT_TYP_REFRESH
    assert "jti" in payload


def test_create_refresh_token_with_jti_returns_expiry():
    token, jti, expires_at = create_refresh_token_with_jti("1")
    assert isinstance(jti, str) and len(jti) > 0
    assert expires_at > datetime.now(UTC)
    payload = decode_token(token)
    assert payload["jti"] == jti


def test_refresh_jti_hash_is_deterministic():
    assert refresh_jti_hash("abc") == refresh_jti_hash("abc")
    assert refresh_jti_hash("abc") != refresh_jti_hash("xyz")


def test_constant_time_equals():
    assert constant_time_equals("same", "same")
    assert not constant_time_equals("a", "b")


def test_safe_decode_token_returns_none_for_garbage():
    assert safe_decode_token("not-a-jwt") is None


def test_safe_decode_token_returns_none_for_wrong_secret():
    settings = get_settings()
    foreign = jwt.encode(
        {"sub": "1", "typ": JWT_TYP_ACCESS},
        "other-secret",
        algorithm=settings.jwt_algorithm,
    )
    assert safe_decode_token(foreign) is None


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"typ": JWT_TYP_ACCESS}, True),
        ({"typ": JWT_TYP_REFRESH}, False),
        ({"typ": None}, True),
        ({}, True),
    ],
)
def test_is_access_token_payload(payload, expected):
    assert is_access_token_payload(payload) is expected


def test_access_token_expires_in_future():
    settings = get_settings()
    token = create_access_token("99")
    payload = decode_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    min_exp = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes - 1)
    assert exp >= min_exp
