import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.middleware.jwt import get_current_user, require_permission
from app.redis_client import close_redis, get_redis
from app.schemas.auth import CurrentUser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(private_key: str, payload_overrides: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "roles": ["viewer"],
        "permissions": ["task:read"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, private_key, algorithm="RS256")


def _make_app(permission: str | None = None) -> FastAPI:
    """Build a tiny FastAPI app for testing."""
    app = FastAPI()
    from fastapi import Depends
    from app.redis_client import get_redis as _get_redis

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    app.dependency_overrides[_get_redis] = lambda: mock_redis

    if permission:

        @app.get("/protected")
        async def protected(user: CurrentUser = require_permission(permission)):
            return {"user_id": str(user.user_id)}

    else:

        @app.get("/protected")
        async def protected_no_perm(user: CurrentUser = Depends(get_current_user)):
            return {"user_id": str(user.user_id)}

    return app, mock_redis


# ---------------------------------------------------------------------------
# CurrentUser schema
# ---------------------------------------------------------------------------


class TestCurrentUser:
    def test_valid(self):
        uid = uuid.uuid4()
        u = CurrentUser(user_id=uid, roles=["admin"], permissions=["task:create"])
        assert u.user_id == uid
        assert u.roles == ["admin"]
        assert u.permissions == ["task:create"]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_public_key_inline(self):
        s = Settings(jwt_public_key="MY_KEY", jwt_public_key_path="")
        assert s.public_key_content == "MY_KEY"

    def test_public_key_from_file(self, tmp_path):
        key_file = tmp_path / "public.pem"
        key_file.write_text("FILE_KEY")
        s = Settings(jwt_public_key="", jwt_public_key_path=str(key_file))
        assert s.public_key_content == "FILE_KEY"

    def test_public_key_missing(self):
        s = Settings(jwt_public_key="", jwt_public_key_path="")
        with pytest.raises(ValueError, match="No JWT public key configured"):
            _ = s.public_key_content


# ---------------------------------------------------------------------------
# Redis client
# ---------------------------------------------------------------------------


class TestRedisClient:
    @pytest.fixture(autouse=True)
    async def reset_redis(self):
        """Ensure _client is None before and after each test."""
        import app.redis_client as rc

        rc._client = None
        yield
        rc._client = None

    async def test_get_redis_creates_client(self):
        import app.redis_client as rc

        mock_client = MagicMock()
        with patch("redis.asyncio.from_url", return_value=mock_client) as mock_from_url:
            client = await rc.get_redis()
            assert client is mock_client
            mock_from_url.assert_called_once()

    async def test_get_redis_singleton(self):
        import app.redis_client as rc

        mock_client = MagicMock()
        with patch("redis.asyncio.from_url", return_value=mock_client):
            c1 = await rc.get_redis()
            c2 = await rc.get_redis()
            assert c1 is c2

    async def test_close_redis(self):
        import app.redis_client as rc

        mock_client = AsyncMock()
        rc._client = mock_client
        await rc.close_redis()
        mock_client.aclose.assert_awaited_once()
        assert rc._client is None

    async def test_close_redis_noop_when_none(self):
        import app.redis_client as rc

        rc._client = None
        await rc.close_redis()  # Should not raise


# ---------------------------------------------------------------------------
# JWT middleware - get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.fixture
    def app_and_redis(self):
        return _make_app(permission=None)

    def test_valid_token(self, rsa_key_pair):
        app, _ = _make_app()
        token = _make_token(rsa_key_pair["private_key"])
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        assert "user_id" in resp.json()

    def test_missing_authorization(self, rsa_key_pair):
        app, _ = _make_app()
        with TestClient(app) as client:
            resp = client.get("/protected")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["detail"]

    def test_expired_token(self, rsa_key_pair):
        app, _ = _make_app()
        token = _make_token(
            rsa_key_pair["private_key"],
            {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        )
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_invalid_signature(self, rsa_key_pair):
        from cryptography.hazmat.primitives.asymmetric import rsa as _rsa

        other_private = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
        from cryptography.hazmat.primitives import serialization

        other_private_pem = other_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        app, _ = _make_app()
        token = _make_token(other_private_pem)  # signed with different key
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["detail"]

    def test_blacklisted_token(self, rsa_key_pair):
        app, mock_redis = _make_app()
        mock_redis.get = AsyncMock(return_value="1")  # blacklisted
        token = _make_token(rsa_key_pair["private_key"])
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401
        assert "revoked" in resp.json()["detail"].lower()

    def test_missing_sub_field(self, rsa_key_pair):
        app, _ = _make_app()
        # Token without "sub"
        now = datetime.now(timezone.utc)
        payload = {
            "email": "x@x.com",
            "roles": [],
            "permissions": [],
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(minutes=15),
        }
        token = jwt.encode(payload, rsa_key_pair["private_key"], algorithm="RS256")
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401
        assert "Invalid token payload" in resp.json()["detail"]

    def test_invalid_uuid_in_sub(self, rsa_key_pair):
        app, _ = _make_app()
        token = _make_token(rsa_key_pair["private_key"], {"sub": "not-a-uuid"})
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401
        assert "Invalid token payload" in resp.json()["detail"]

    def test_token_without_jti(self, rsa_key_pair):
        """Token without jti should still be accepted (no blacklist check)."""
        app, _ = _make_app()
        # Remove jti key entirely
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "user@example.com",
            "roles": ["viewer"],
            "permissions": ["task:read"],
            "iat": now,
            "exp": now + timedelta(minutes=15),
        }
        token = jwt.encode(payload, rsa_key_pair["private_key"], algorithm="RS256")
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# require_permission decorator
# ---------------------------------------------------------------------------


class TestRequirePermission:
    def test_has_permission(self, rsa_key_pair):
        app, _ = _make_app(permission="task:read")
        token = _make_token(rsa_key_pair["private_key"], {"permissions": ["task:read"]})
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_missing_permission(self, rsa_key_pair):
        app, _ = _make_app(permission="task:create")
        token = _make_token(rsa_key_pair["private_key"], {"permissions": ["task:read"]})
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 403
        assert "task:create" in resp.json()["detail"]

    def test_multiple_permissions_sufficient(self, rsa_key_pair):
        app, _ = _make_app(permission="task:create")
        token = _make_token(
            rsa_key_pair["private_key"],
            {"permissions": ["task:read", "task:create", "task:delete"]},
        )
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_no_permissions_in_token(self, rsa_key_pair):
        app, _ = _make_app(permission="task:create")
        token = _make_token(rsa_key_pair["private_key"], {"permissions": []})
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# main.py
# ---------------------------------------------------------------------------


class TestMain:
    def test_health(self):
        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_shutdown_closes_redis(self):
        import app.redis_client as rc

        mock_client = AsyncMock()
        rc._client = mock_client
        from app.main import shutdown

        await shutdown()
        mock_client.aclose.assert_awaited_once()
        rc._client = None
