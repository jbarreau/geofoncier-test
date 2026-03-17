"""
E2E test configuration.

Assumes all 3 services are running via docker-compose (docker compose up --build -d).
The docker-compose stack handles key generation, migrations, and seed data automatically.

Service URLs and DB DSN can be overridden via environment variables:
  E2E_AUTH_URL        (default: http://localhost:8000)
  E2E_TASK_URL        (default: http://localhost:8001)
  E2E_ANALYTICS_URL   (default: http://localhost:8002)
  E2E_DB_DSN          (default: postgresql://geofoncier:geofoncier@localhost:5432/geofoncier)
"""

import os
import uuid
from collections.abc import AsyncGenerator

import asyncpg
import httpx
import pytest

AUTH_URL = os.environ.get("E2E_AUTH_URL", "http://localhost:8000")
TASK_URL = os.environ.get("E2E_TASK_URL", "http://localhost:8001")
ANALYTICS_URL = os.environ.get("E2E_ANALYTICS_URL", "http://localhost:8002")
DB_DSN = os.environ.get(
    "E2E_DB_DSN",
    "postgresql://geofoncier:geofoncier@localhost:5432/geofoncier",
)

# Unique run ID — namespaces all test users so multiple runs don't collide.
RUN_ID = uuid.uuid4().hex[:8]
TEST_PASSWORD = "TestPass123!"


# ---------------------------------------------------------------------------
# Infrastructure fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def db_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    conn = await asyncpg.connect(DB_DSN)
    yield conn
    await conn.close()


@pytest.fixture(scope="session")
async def auth_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=AUTH_URL, timeout=10.0) as client:
        yield client


@pytest.fixture(scope="session")
async def task_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=TASK_URL, timeout=10.0) as client:
        yield client


@pytest.fixture(scope="session")
async def analytics_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=ANALYTICS_URL, timeout=10.0) as client:
        yield client


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def registered_users(
    auth_client: httpx.AsyncClient,
    db_conn: asyncpg.Connection,
) -> dict:
    """
    Register 3 test users and assign roles via DB.

    Roles (from scripts/seed.py):
      viewer: task:read, analytics:read
      user:   task:create, task:read, task:update
      admin:  task:create, task:read, task:update, task:delete,
              analytics:read, analytics:admin, users:manage

    Each registered user gets the "viewer" role automatically (auth-service behaviour).
    Extra roles are added via direct DB insert.
    """
    role_extra: dict[str, list[str]] = {
        "viewer": [],        # viewer role only (assigned by register)
        "user": ["user"],    # viewer + user
        "admin": ["admin"],  # viewer + admin
    }

    users: dict[str, dict] = {}

    for key, extra_roles in role_extra.items():
        email = f"e2e_{key}_{RUN_ID}@example.com"
        resp = await auth_client.post(
            "/auth/register",
            json={"email": email, "password": TEST_PASSWORD},
        )
        assert resp.status_code == 201, f"Register '{key}' failed: {resp.text}"
        data = resp.json()
        users[key] = {"id": uuid.UUID(data["id"]), "email": email}

        for role_name in extra_roles:
            role_id = await db_conn.fetchval(
                "SELECT id FROM auth.roles WHERE name = $1", role_name
            )
            assert role_id is not None, (
                f"Role '{role_name}' not found — ensure docker-compose seed ran."
            )
            await db_conn.execute(
                """
                INSERT INTO auth.user_roles (user_id, role_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
                """,
                users[key]["id"],
                role_id,
            )

    return users


@pytest.fixture(scope="session")
async def tokens(
    auth_client: httpx.AsyncClient,
    registered_users: dict,
) -> dict:
    """Login each test user and return their token pairs."""
    result: dict[str, dict] = {}
    for key, user in registered_users.items():
        resp = await auth_client.post(
            "/auth/login",
            json={"email": user["email"], "password": TEST_PASSWORD},
        )
        assert resp.status_code == 200, f"Login '{key}' failed: {resp.text}"
        data = resp.json()
        result[key] = {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
        }
    return result


@pytest.fixture(scope="session")
def viewer_token(tokens: dict) -> str:
    return tokens["viewer"]["access_token"]


@pytest.fixture(scope="session")
def user_token(tokens: dict) -> str:
    return tokens["user"]["access_token"]


@pytest.fixture(scope="session")
def admin_token(tokens: dict) -> str:
    return tokens["admin"]["access_token"]


# ---------------------------------------------------------------------------
# Task seed fixture (used by analytics tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def created_tasks(
    task_client: httpx.AsyncClient,
    admin_token: str,
) -> list[str]:
    """
    Create 5 sample tasks via the task-service API.
    Used to ensure analytics endpoints have data to aggregate.

    Task breakdown:
      - 2 todo tasks with future due dates
      - 2 doing tasks with past due dates (overdue)
      - 1 done task with a past due date (NOT counted as overdue)
    """
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    headers = {"Authorization": f"Bearer {admin_token}"}

    task_specs = [
        {
            "title": f"E2E todo-future-1 {RUN_ID}",
            "status": "todo",
            "due_date": (now + timedelta(days=7)).isoformat(),
        },
        {
            "title": f"E2E todo-future-2 {RUN_ID}",
            "status": "todo",
            "due_date": (now + timedelta(days=14)).isoformat(),
        },
        {
            "title": f"E2E doing-overdue-1 {RUN_ID}",
            "status": "doing",
            "due_date": (now - timedelta(days=1)).isoformat(),
        },
        {
            "title": f"E2E doing-overdue-2 {RUN_ID}",
            "status": "doing",
            "due_date": (now - timedelta(days=2)).isoformat(),
        },
        {
            "title": f"E2E done-past {RUN_ID}",
            "status": "done",
            "due_date": (now - timedelta(days=3)).isoformat(),
        },
    ]

    task_ids: list[str] = []
    for spec in task_specs:
        resp = await task_client.post("/tasks", json=spec, headers=headers)
        assert resp.status_code == 201, f"Create task failed: {resp.text}"
        task_ids.append(resp.json()["id"])

    return task_ids
