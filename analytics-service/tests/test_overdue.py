"""Tests for GET /analytics/overdue."""

from datetime import datetime, timedelta, timezone

from app.constants import PERM_ANALYTICS_READ
from app.database import get_db
from app.main import app

from .helpers import make_fake_task, make_mock_db_rows, make_token


class TestOverdue:
    async def test_no_auth_returns_401(self, client):
        resp = await client.get("/analytics/overdue")
        assert resp.status_code == 401

    async def test_missing_permission_returns_403(self, client, rsa_key_pair):
        token = make_token(rsa_key_pair["private_key"], permissions=["task:read"])
        resp = await client.get(
            "/analytics/overdue", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    async def test_returns_overdue_tasks(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        past = datetime.now(timezone.utc) - timedelta(days=2)
        tasks = [
            make_fake_task(status="todo", due_date=past),
            make_fake_task(status="doing", due_date=past),
        ]
        mock_db = make_mock_db_rows(tasks)

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            "/analytics/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["tasks"]) == 2

    async def test_empty_when_no_overdue(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        mock_db = make_mock_db_rows([])

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            "/analytics/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        assert resp.json() == {"count": 0, "tasks": []}

    async def test_custom_limit_accepted(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        mock_db = make_mock_db_rows([])

        app.dependency_overrides[get_db] = lambda: mock_db
        resp = await client.get(
            "/analytics/overdue?limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200

    async def test_limit_above_max_returns_422(self, client, rsa_key_pair):
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        # get_db overridden so FastAPI can reach param validation without a real DB
        app.dependency_overrides[get_db] = lambda: make_mock_db_rows([])
        resp = await client.get(
            "/analytics/overdue?limit=9999",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)
        assert resp.status_code == 422
