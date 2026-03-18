from unittest.mock import AsyncMock

from app.exceptions import EmailAlreadyExistsError

from .helpers import make_user


class TestRegister:
    async def test_success_returns_201_without_password(self, client, mocker):
        mocker.patch(
            "app.routes.auth.register_user", AsyncMock(return_value=make_user())
        )

        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "securepass123",
            },
        )

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

        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "taken@example.com",
                "password": "securepass123",
            },
        )

        assert resp.status_code == 409

    async def test_invalid_email_returns_422(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepass123",
            },
        )

        assert resp.status_code == 422

    async def test_password_too_short_returns_422(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",
            },
        )

        assert resp.status_code == 422

    async def test_password_too_long_returns_422(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "x" * 129,
            },
        )

        assert resp.status_code == 422

    async def test_missing_password_returns_422(self, client):
        resp = await client.post("/api/auth/register", json={"email": "user@example.com"})

        assert resp.status_code == 422

    async def test_missing_email_returns_422(self, client):
        resp = await client.post("/api/auth/register", json={"password": "securepass123"})

        assert resp.status_code == 422
