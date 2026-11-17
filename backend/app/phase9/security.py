from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from urllib.parse import urlsplit, urlunsplit

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


ROLES = {"admin", "operator", "reviewer"}
bearer = HTTPBearer(auto_error=False)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${_b64(salt)}${_b64(digest)}"


def password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, _unb64(expected))
    except (ValueError, TypeError):
        return False


def _secret() -> bytes:
    value = os.environ.get("JWT_SECRET")
    if not value or len(value) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")
    return value.encode()


def issue_token(username: str, role: str, expires_seconds: int = 3600) -> str:
    if role not in ROLES:
        raise ValueError("invalid role")
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "role": role, "exp": int(time.time()) + expires_seconds}
    encoded = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}.{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = _b64(hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def decode_token(token: str) -> dict:
    try:
        encoded, signature = token.rsplit(".", 1)
        expected = _b64(hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(_unb64(encoded.split(".", 1)[1]))
        if int(payload["exp"]) <= int(time.time()) or payload.get("role") not in ROLES:
            raise ValueError
        return payload
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer token required")
    return decode_token(credentials.credentials)


def require_roles(*roles: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user
    return dependency


def redact_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1***", value)
    value = re.sub(r"(?i)(password|passwd|token|secret|authorization|database_url)\s*[=:]\s*[^\s,;]+", r"\1=***", value)
    try:
        parsed = urlsplit(value)
        if parsed.username or parsed.password:
            host = parsed.hostname or ""
            if parsed.port:
                host += f":{parsed.port}"
            value = urlunsplit((parsed.scheme, f"***:***@{host}", parsed.path, parsed.query, parsed.fragment))
    except ValueError:
        pass
    return value
