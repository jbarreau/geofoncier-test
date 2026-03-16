import uuid
from unittest.mock import AsyncMock


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
