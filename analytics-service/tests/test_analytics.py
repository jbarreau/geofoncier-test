"""Tests for analytics endpoints.

DB interactions are mocked — the service is read-only so no real DB needed.
JWT auth uses a real in-memory RSA key pair (see conftest.py).
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.constants import PERM_ANALYTICS_ADMIN, PERM_ANALYTICS_READ
from app.database import get_db
from app.main import app
from app.redis_client import get_redis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = str(uuid.uuid4())
OWNER_A = uuid.uuid4()
OWNER_B = uuid.uuid4()


def make_token(
    private_key: str,
    permissions: list[str],
    roles: list[str] | None = None,
    expired: bool = False,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now - timedelta(minutes=1) if expired else now + timedelta(minutes=15)
    payload = {
        "sub": USER_ID,
        "email": "user@example.com",
        "roles": roles or [],
        "permissions": permissions,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def make_fake_task(
    status: str = "todo",
    due_date: datetime | None = None,
    owner_id: uuid.UUID | None = None,
):
    task = MagicMock()
    task.id = uuid.uuid4()
    task.title = "Test task"
    task.status = status
    task.owner_id = owner_id or OWNER_A
    task.due_date = due_date
    return task


def make_mock_db_scalars(results: list) -> AsyncMock:
    """Mock DB whose execute() result is directly iterable (GROUP BY queries)."""
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter(results))
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


def make_mock_db_rows(results: list) -> AsyncMock:
    """Mock DB whose execute().all() returns results (column-select queries)."""
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=results)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


# ---------------------------------------------------------------------------
# Fake Redis helpers
# ---------------------------------------------------------------------------


class FakeRedis:
    async def get(self, key: str):
        return None


class BlacklistRedis:
    async def get(self, key: str):
        return "1"


# ---------------------------------------------------------------------------
# Client fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    app.dependency_overrides[get_redis] = lambda: FakeRedis()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# /analytics/summary
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# /analytics/overdue
# ---------------------------------------------------------------------------


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
        # get_db is overridden so FastAPI can reach param validation cleanly
        app.dependency_overrides[get_db] = lambda: make_mock_db_rows([])
        resp = await client.get(
            "/analytics/overdue?limit=9999",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /analytics/by-user
# ---------------------------------------------------------------------------


class TestByUser:
    async def test_no_auth_returns_401(self, client):
        resp = await client.get("/analytics/by-user")
        assert resp.status_code == 401

    async def test_analytics_read_not_enough(self, client, rsa_key_pair):
        """analytics:read is insufficient - admin only."""
        token = make_token(
            rsa_key_pair["private_key"], permissions=[PERM_ANALYTICS_READ]
        )
        resp = await client.get(
            "/analytics/by-user", headers={"Authorization": f"Bearer {token}"}
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
            "/analytics/by-user",
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
            "/analytics/by-user",
            headers={"Authorization": f"Bearer {token}"},
        )
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
