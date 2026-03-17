"""Tests for middleware/jwt.py — missing-payload edge cases."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization as _ser
from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
from httpx import ASGITransport, AsyncClient

from app.main import app
from geofoncier_shared.redis.redis_client import get_redis

USER_ID = str(uuid.uuid4())


def make_token(
    private_key: str, *, sub: str = USER_ID, include_sub: bool = True
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict = {
        "email": "u@example.com",
        "roles": [],
        "permissions": [],
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    if include_sub:
        payload["sub"] = sub
    return jwt.encode(payload, private_key, algorithm="RS256")


class FakeRedis:
    async def get(self, _key: str):
        return None


class TestJWTMiddlewareEdgeCases:
    async def test_missing_sub_returns_401(self, rsa_key_pair):
        """Token without 'sub' claim → invalid payload."""
        token = make_token(rsa_key_pair["private_key"], include_sub=False)
        app.dependency_overrides[get_redis] = lambda: FakeRedis()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token payload"

    async def test_invalid_sub_uuid_returns_401(self, rsa_key_pair):
        """'sub' is present but not a valid UUID."""
        token = make_token(rsa_key_pair["private_key"], sub="not-a-uuid")
        app.dependency_overrides[get_redis] = lambda: FakeRedis()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token payload"

    async def test_wrong_signature_returns_401(self, rsa_key_pair):
        """Token signed with a different private key."""
        other_key = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_private_pem = other_key.private_bytes(
            encoding=_ser.Encoding.PEM,
            format=_ser.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=_ser.NoEncryption(),
        ).decode()

        token = make_token(other_private_pem)
        app.dependency_overrides[get_redis] = lambda: FakeRedis()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token"
