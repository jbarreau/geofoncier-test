"""Tests for GET /analytics/summary."""

from unittest.mock import MagicMock

from app.constants import PERM_ANALYTICS_READ
from app.database import get_db
from app.main import app
from app.redis_client import get_redis

from .helpers import BlacklistRedis, make_mock_db_scalars, make_token


class TestSummary:
    async def test_no_auth_returns_401(self, client):
        resp = await client.get("/analytics/summary")
        assert resp.status_code == 401

    async def test_missing_permission_returns_403(self, client, rsa_key_pair):
        token = make_token(rsa_key_pair["private_key"], permissions=[])
        resp = await client.get(
            "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    async def test_returns_counts_by_status(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        fake_rows = [
            MagicMock(status="todo", count=3),
            MagicMock(status="doing", count=1),
            MagicMock(status="done", count=5),
        ]
        mock_db = make_mock_db_scalars(fake_rows)

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            "/analytics/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 9
        statuses = {s["status"]: s["count"] for s in data["by_status"]}
        assert statuses["todo"] == 3
        assert statuses["doing"] == 1
        assert statuses["done"] == 5

    async def test_expired_token_returns_401(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"],
            permissions=[PERM_ANALYTICS_READ],
            expired=True,
        )
        resp = await client.get(
            "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Token has expired"

    async def test_blacklisted_token_returns_401(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        app.dependency_overrides[get_redis] = lambda: BlacklistRedis()
        resp = await client.get(
            "/analytics/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Token has been revoked"
