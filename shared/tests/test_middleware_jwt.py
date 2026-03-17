"""Tests for geofoncier_shared.fastapi.middleware.jwt."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from geofoncier_shared.fastapi.middleware.jwt import (
    get_current_user,
    require_permission,
)
from geofoncier_shared.fastapi.schemas.auth import CurrentUser
from geofoncier_shared.redis.redis_client import get_redis

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


def _make_app(permission: str | None = None):
    """Build a minimal FastAPI app.  JWT_PUBLIC_KEY must be set in the environment."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    app = FastAPI()
    app.dependency_overrides[get_redis] = lambda: mock_redis

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
# get_current_user dependency
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.fixture(autouse=True)
    def patch_jwt_env(self, rsa_key_pair, monkeypatch):
        monkeypatch.setenv("JWT_PUBLIC_KEY", rsa_key_pair["public_key"])
        monkeypatch.delenv("JWT_PUBLIC_KEY_PATH", raising=False)

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
        other_private = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_private_pem = other_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        app, _ = _make_app()
        token = _make_token(other_private_pem)
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401
        assert "Invalid token" in resp.json()["detail"]

    def test_blacklisted_token(self, rsa_key_pair):
        app, mock_redis = _make_app()
        mock_redis.get = AsyncMock(return_value="1")
        token = _make_token(rsa_key_pair["private_key"])
        with TestClient(app) as client:
            resp = client.get(
                "/protected", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 401
        assert "revoked" in resp.json()["detail"].lower()

    def test_missing_sub_field(self, rsa_key_pair):
        app, _ = _make_app()
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
        """Token without jti should be accepted (no blacklist check)."""
        app, _ = _make_app()
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

    def test_missing_public_key_raises(self, monkeypatch):
        monkeypatch.delenv("JWT_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("JWT_PUBLIC_KEY_PATH", raising=False)
        app, _ = _make_app()
        with pytest.raises(ValueError, match="No JWT public key configured"):
            with TestClient(app) as client:
                client.get("/protected", headers={"Authorization": "Bearer x"})


# ---------------------------------------------------------------------------
# require_permission dependency
# ---------------------------------------------------------------------------


class TestRequirePermission:
    @pytest.fixture(autouse=True)
    def patch_jwt_env(self, rsa_key_pair, monkeypatch):
        monkeypatch.setenv("JWT_PUBLIC_KEY", rsa_key_pair["public_key"])
        monkeypatch.delenv("JWT_PUBLIC_KEY_PATH", raising=False)

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
