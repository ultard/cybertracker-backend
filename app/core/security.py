from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from hmac import new as hmac_new
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

_settings = get_settings()

JWT_TYP_ACCESS = "access"
JWT_TYP_REFRESH = "refresh"


def hash_password(password: str) -> str:
    data = password.encode("utf-8")
    if len(data) > 72:
        data = data[:72]
    return bcrypt.hashpw(data, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, extra: dict | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=_settings.access_token_expire_minutes)
    payload: dict = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    payload["typ"] = JWT_TYP_ACCESS
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    token, _jti, _expires_at = create_refresh_token_with_jti(subject)
    return token


def create_refresh_token_with_jti(subject: str) -> tuple[str, str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(days=_settings.refresh_token_expire_days)
    jti = uuid4().hex
    payload = {"sub": subject, "exp": expires_at, "typ": JWT_TYP_REFRESH, "jti": jti}
    token = jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)
    return token, jti, expires_at


def refresh_jti_hash(jti: str) -> str:
    mac = hmac_new(
        _settings.jwt_secret_key.encode("utf-8"), jti.encode("utf-8"), sha256
    ).hexdigest()
    return mac


def constant_time_equals(a: str, b: str) -> bool:
    return compare_digest(a, b)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _settings.jwt_secret_key, algorithms=[_settings.jwt_algorithm])


def safe_decode_token(token: str) -> dict | None:
    try:
        return decode_token(token)
    except JWTError:
        return None


def is_access_token_payload(payload: dict) -> bool:
    typ = payload.get("typ")
    if typ == JWT_TYP_REFRESH:
        return False
    return typ in (None, JWT_TYP_ACCESS)
