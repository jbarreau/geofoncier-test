"""Shared test utilities for analytics-service tests."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import jwt

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


class FakeRedis:
    async def get(self, key: str):
        return None


class BlacklistRedis:
    async def get(self, key: str):
        return "1"
