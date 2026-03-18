"""Tests for GET /analytics/by-user."""

from unittest.mock import MagicMock

from app.constants import PERM_ANALYTICS_ADMIN, PERM_ANALYTICS_READ
from app.database import get_db
from app.main import app

from .helpers import OWNER_A, OWNER_B, make_mock_db_scalars, make_token


class TestByUser:
    async def test_no_auth_returns_401(self, client):
        resp = await client.get("/api/analytics/by-user")
        assert resp.status_code == 401

    async def test_analytics_read_not_enough(self, client, rsa_key_pair):
        """analytics:read is insufficient — admin only."""
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        resp = await client.get(
            "/api/analytics/by-user", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    async def test_admin_returns_counts_by_user(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_ADMIN]
        )
        fake_rows = [
            MagicMock(owner_id=OWNER_A, count=4),
            MagicMock(owner_id=OWNER_B, count=2),
        ]
        mock_db = make_mock_db_scalars(fake_rows)

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            "/api/analytics/by-user",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        data = resp.json()
        by_user = {u["owner_id"]: u["count"] for u in data["by_user"]}
        assert by_user[str(OWNER_A)] == 4
        assert by_user[str(OWNER_B)] == 2

    async def test_analytics_admin_also_passes_permission_check(
        self, client, rsa_key_pair
    ):
        """Sanity: analytics:admin alone (without analytics:read) is enough for by-user."""
        token = make_token(
            rsa_key_pair["private_key"],
            permissions=[PERM_ANALYTICS_ADMIN],
        )
        mock_db = make_mock_db_scalars([])

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            "/api/analytics/by-user",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
