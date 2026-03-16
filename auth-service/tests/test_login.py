from unittest.mock import AsyncMock

from app.exceptions import InactiveUserError, InvalidCredentialsError

from .helpers import make_tokens


class TestLogin:
    async def test_success_returns_token_pair(self, client, mocker):
        mocker.patch("app.routes.auth.login_user", AsyncMock(return_value=make_tokens()))

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

    async def test_missing_email_returns_422(self, client):
        resp = await client.post("/auth/login", json={"password": "securepass123"})

        assert resp.status_code == 422
