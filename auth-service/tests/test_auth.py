"""
Unit tests for auth-service HTTP endpoints.

Strategy: service functions (register_user, login_user, refresh_tokens, logout_user)
are mocked at the route import level so tests cover request parsing, response
serialisation, and error propagation without touching the database or Redis.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.schemas import TokenResponse, UserResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email: str = "user@example.com") -> UserResponse:
    return UserResponse(
        id=uuid.uuid4(),
        email=email,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def _make_tokens() -> TokenResponse:
    return TokenResponse(
        access_token="header.payload.sig",
        refresh_token=f"{uuid.uuid4()}:{uuid.uuid4()}",
    )


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

class TestRegister:
    async def test_success_returns_201_without_password(self, client, mocker):
        mocker.patch("app.routes.auth.register_user", AsyncMock(return_value=_make_user()))

        resp = await client.post("/auth/register", json={
            "email": "user@example.com",
            "password": "securepass123",
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "user@example.com"
        assert data["is_active"] is True
        assert "hashed_password" not in data
        assert "password" not in data

    async def test_duplicate_email_returns_409(self, client, mocker):
        mocker.patch(
            "app.routes.auth.register_user",
            AsyncMock(side_effect=EmailAlreadyExistsError()),
        )

        resp = await client.post("/auth/register", json={
            "email": "taken@example.com",
            "password": "securepass123",
        })

        assert resp.status_code == 409

    async def test_invalid_email_returns_422(self, client):
        resp = await client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "securepass123",
        })

        assert resp.status_code == 422

    async def test_password_too_short_returns_422(self, client):
        resp = await client.post("/auth/register", json={
            "email": "user@example.com",
            "password": "short",
        })

        assert resp.status_code == 422

    async def test_password_too_long_returns_422(self, client):
        resp = await client.post("/auth/register", json={
            "email": "user@example.com",
            "password": "x" * 129,
        })

        assert resp.status_code == 422

    async def test_missing_password_returns_422(self, client):
        resp = await client.post("/auth/register", json={"email": "user@example.com"})

        assert resp.status_code == 422

    async def test_missing_email_returns_422(self, client):
        resp = await client.post("/auth/register", json={"password": "securepass123"})

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    async def test_success_returns_token_pair(self, client, mocker):
        mocker.patch("app.routes.auth.login_user", AsyncMock(return_value=_make_tokens()))

        resp = await client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "securepass123",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_wrong_password_returns_401(self, client, mocker):
        mocker.patch(
            "app.routes.auth.login_user",
            AsyncMock(side_effect=InvalidCredentialsError()),
        )

        resp = await client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "wrongpassword",
        })

        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Bearer"

    async def test_unknown_email_returns_401(self, client, mocker):
        mocker.patch(
            "app.routes.auth.login_user",
            AsyncMock(side_effect=InvalidCredentialsError()),
        )

        resp = await client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "securepass123",
        })

        assert resp.status_code == 401

    async def test_inactive_user_returns_403(self, client, mocker):
        mocker.patch(
            "app.routes.auth.login_user",
            AsyncMock(side_effect=InactiveUserError()),
        )

        resp = await client.post("/auth/login", json={
            "email": "inactive@example.com",
            "password": "securepass123",
        })

        assert resp.status_code == 403

    async def test_missing_fields_returns_422(self, client):
        resp = await client.post("/auth/login", json={"password": "securepass123"})

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

class TestRefresh:
    async def test_success_returns_new_token_pair(self, client, mocker):
        new_tokens = _make_tokens()
        mock_refresh = mocker.patch(
            "app.routes.auth.refresh_tokens",
            AsyncMock(return_value=new_tokens),
        )

        resp = await client.post("/auth/refresh", json={
            "refresh_token": f"{uuid.uuid4()}:{uuid.uuid4()}",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == new_tokens.access_token
        assert data["refresh_token"] == new_tokens.refresh_token
        mock_refresh.assert_awaited_once()

    async def test_invalid_token_returns_401(self, client, mocker):
        mocker.patch(
            "app.routes.auth.refresh_tokens",
            AsyncMock(side_effect=InvalidRefreshTokenError()),
        )

        resp = await client.post("/auth/refresh", json={"refresh_token": "bad-token"})

        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Bearer"

    async def test_revoked_token_returns_401(self, client, mocker):
        mocker.patch(
            "app.routes.auth.refresh_tokens",
            AsyncMock(side_effect=InvalidRefreshTokenError()),
        )

        resp = await client.post("/auth/refresh", json={
            "refresh_token": f"{uuid.uuid4()}:{uuid.uuid4()}",
        })

        assert resp.status_code == 401

    async def test_missing_token_returns_422(self, client):
        resp = await client.post("/auth/refresh", json={})

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

class TestLogout:
    async def test_success_returns_204_no_body(self, client, mocker):
        mock_logout = mocker.patch(
            "app.routes.auth.logout_user",
            AsyncMock(return_value=None),
        )

        resp = await client.post("/auth/logout", json={
            "access_token": "header.payload.sig",
            "refresh_token": f"{uuid.uuid4()}:{uuid.uuid4()}",
        })

        assert resp.status_code == 204
        assert resp.content == b""
        mock_logout.assert_awaited_once()

    async def test_logout_called_with_correct_tokens(self, client, mocker):
        mock_logout = mocker.patch(
            "app.routes.auth.logout_user",
            AsyncMock(return_value=None),
        )
        access = "header.payload.sig"
        refresh = f"{uuid.uuid4()}:{uuid.uuid4()}"

        await client.post("/auth/logout", json={
            "access_token": access,
            "refresh_token": refresh,
        })

        _db, _redis, at, rt = mock_logout.call_args.args
        assert at == access
        assert rt == refresh

    async def test_missing_access_token_returns_422(self, client):
        resp = await client.post("/auth/logout", json={
            "refresh_token": f"{uuid.uuid4()}:{uuid.uuid4()}",
        })

        assert resp.status_code == 422

    async def test_missing_refresh_token_returns_422(self, client):
        resp = await client.post("/auth/logout", json={
            "access_token": "header.payload.sig",
        })

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /auth/.well-known/jwks.json
# ---------------------------------------------------------------------------

class TestJwks:
    async def test_returns_valid_rsa_jwks(self, client):
        resp = await client.get("/auth/.well-known/jwks.json")

        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert len(data["keys"]) == 1
        key = data["keys"][0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert key["use"] == "sig"
        assert key["kid"] == "auth-service-rs256"
        assert "n" in key and len(key["n"]) > 0
        assert "e" in key and len(key["e"]) > 0


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealth:
    async def test_health_check(self, client):
        resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
