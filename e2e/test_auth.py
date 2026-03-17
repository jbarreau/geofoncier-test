"""
Auth-service end-to-end tests.

Each test registers its own unique user to remain independently runnable
and free of state dependencies on session fixtures.
"""

import uuid

import httpx
import pytest


def _unique_email(label: str) -> str:
    return f"e2e_{label}_{uuid.uuid4().hex[:8]}@example.com"


PASSWORD = "TestPass123!"


class TestRegister:
    async def test_register_success(self, auth_client: httpx.AsyncClient) -> None:
        resp = await auth_client.post(
            "/auth/register",
            json={"email": _unique_email("reg"), "password": PASSWORD},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["is_active"] is True
        assert "id" in body
        assert "@example.com" in body["email"]

    async def test_register_duplicate_email_returns_409(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        email = _unique_email("dup")
        await auth_client.post(
            "/auth/register", json={"email": email, "password": PASSWORD}
        )
        resp = await auth_client.post(
            "/auth/register", json={"email": email, "password": PASSWORD}
        )
        assert resp.status_code == 409

    async def test_register_invalid_email_returns_422(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        resp = await auth_client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": PASSWORD},
        )
        assert resp.status_code == 422

    async def test_register_short_password_returns_422(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        resp = await auth_client.post(
            "/auth/register",
            json={"email": _unique_email("short"), "password": "abc"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success_returns_token_pair(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        email = _unique_email("login")
        await auth_client.post(
            "/auth/register", json={"email": email, "password": PASSWORD}
        )
        resp = await auth_client.post(
            "/auth/login", json={"email": email, "password": PASSWORD}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        email = _unique_email("loginbad")
        await auth_client.post(
            "/auth/register", json={"email": email, "password": PASSWORD}
        )
        resp = await auth_client.post(
            "/auth/login", json={"email": email, "password": "WrongPass99!"}
        )
        assert resp.status_code == 401

    async def test_login_unknown_user_returns_401(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        resp = await auth_client.post(
            "/auth/login",
            json={"email": "nobody@nowhere.invalid", "password": PASSWORD},
        )
        assert resp.status_code == 401


class TestJWKS:
    async def test_jwks_returns_rsa_key(self, auth_client: httpx.AsyncClient) -> None:
        resp = await auth_client.get("/auth/.well-known/jwks.json")
        assert resp.status_code == 200
        body = resp.json()
        assert "keys" in body
        key = body["keys"][0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert "n" in key
        assert "e" in key


class TestRefresh:
    async def _create_user_and_login(
        self, auth_client: httpx.AsyncClient
    ) -> dict:
        email = _unique_email("refresh")
        await auth_client.post(
            "/auth/register", json={"email": email, "password": PASSWORD}
        )
        resp = await auth_client.post(
            "/auth/login", json={"email": email, "password": PASSWORD}
        )
        assert resp.status_code == 200
        return resp.json()

    async def test_refresh_returns_new_token_pair(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        tokens = await self._create_user_and_login(auth_client)
        resp = await auth_client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"] != tokens["access_token"]
        assert body["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_token_rotation_reuse_fails(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        """Using the same refresh token twice must fail (rotation)."""
        tokens = await self._create_user_and_login(auth_client)
        old_refresh = tokens["refresh_token"]

        first = await auth_client.post(
            "/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert first.status_code == 200

        second = await auth_client.post(
            "/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert second.status_code == 401

    async def test_refresh_invalid_token_returns_401(
        self, auth_client: httpx.AsyncClient
    ) -> None:
        resp = await auth_client.post(
            "/auth/refresh", json={"refresh_token": "not-a-valid-token"}
        )
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_returns_204(self, auth_client: httpx.AsyncClient) -> None:
        email = _unique_email("logout")
        await auth_client.post(
            "/auth/register", json={"email": email, "password": PASSWORD}
        )
        login = await auth_client.post(
            "/auth/login", json={"email": email, "password": PASSWORD}
        )
        tokens = login.json()

        resp = await auth_client.post(
            "/auth/logout",
            json={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert resp.status_code == 204
