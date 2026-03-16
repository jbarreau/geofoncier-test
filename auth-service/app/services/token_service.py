import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import settings


def _bcrypt_safe(value: str) -> bytes:
    """SHA-256 pre-hash to stay within bcrypt's 72-byte input limit."""
    return hashlib.sha256(value.encode()).digest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    roles: list[str],
    permissions: list[str],
) -> tuple[str, str, datetime]:
    """Returns (encoded_jwt, jti, expires_at)."""
    jti = str(uuid.uuid4())
    now = _utcnow()
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "permissions": permissions,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }

    encoded = jwt.encode(payload, settings.private_key_content, algorithm="RS256")
    return encoded, jti, expires_at


def create_refresh_token() -> tuple[str, str, datetime, uuid.UUID]:
    """Returns (raw_token, token_hash, expires_at, db_id).

    raw_token format: "{db_id}:{secret}" — embeds the DB row UUID for O(1) lookup.
    """
    db_id = uuid.uuid4()
    secret = str(uuid.uuid4())
    raw = f"{db_id}:{secret}"
    token_hash = bcrypt.hashpw(_bcrypt_safe(raw), bcrypt.gensalt()).decode()
    expires_at = _utcnow() + timedelta(days=settings.refresh_token_expire_days)
    return raw, token_hash, expires_at, db_id


def verify_refresh_token(raw: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_safe(raw), stored_hash.encode())
    except ValueError:
        return False


def decode_access_token(token: str) -> dict:
    """Decode and verify an access token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.public_key_content, algorithms=["RS256"])
