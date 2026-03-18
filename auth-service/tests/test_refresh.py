import uuid
from unittest.mock import AsyncMock

from app.exceptions import InvalidRefreshTokenError

from .helpers import make_tokens


class TestRefresh:
    async def test_success_returns_new_token_pair(self, client, mocker):
        new_tokens = make_tokens()
        mock_refresh = mocker.patch(
            "app.routes.auth.refresh_tokens",
            AsyncMock(return_value=new_tokens),
        )

        resp = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": f"{uuid.uuid4()}:{uuid.uuid4()}",
            },
        )

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

        resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": "bad-token"}
        )

        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Bearer"

    async def test_revoked_token_returns_401(self, client, mocker):
        mocker.patch(
            "app.routes.auth.refresh_tokens",
            AsyncMock(side_effect=InvalidRefreshTokenError()),
        )

        resp = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": f"{uuid.uuid4()}:{uuid.uuid4()}",
            },
        )

        assert resp.status_code == 401

    async def test_missing_token_returns_422(self, client):
        resp = await client.post("/api/auth/refresh", json={})

        assert resp.status_code == 422
