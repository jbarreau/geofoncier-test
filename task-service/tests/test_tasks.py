"""Tests for /tasks CRUD endpoints."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.task import Task, TaskStatus
from app.redis_client import get_redis

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(
    private_key: str,
    user_id: str | None = None,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "roles": roles if roles is not None else ["editor"],
        "permissions": permissions
        if permissions is not None
        else ["task:create", "task:read", "task:update", "task:delete"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def _make_task(
    owner_id: uuid.UUID | None = None,
    status: TaskStatus = TaskStatus.pending,
) -> Task:
    task = Task(
        title="Test task",
        description="A description",
        status=status,
        owner_id=owner_id or uuid.uuid4(),
    )
    task.id = uuid.uuid4()
    task.created_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    return task


@pytest.fixture()
def client(rsa_key_pair):
    """TestClient with mocked Redis (no blacklist) and mocked DB session."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    mock_db = AsyncMock()

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db

    with TestClient(app) as c:
        c._private_key = rsa_key_pair["private_key"]
        yield c

    app.dependency_overrides.clear()


def auth_headers(client, *, roles=None, permissions=None, user_id=None):
    token = _make_token(
        client._private_key,
        user_id=user_id,
        roles=roles,
        permissions=permissions,
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /tasks
# ---------------------------------------------------------------------------


class TestCreateTask:
    def test_creates_task(self, client):
        task = _make_task()
        with patch("app.routes.tasks.svc.create_task", new_callable=AsyncMock, return_value=task):
            resp = client.post(
                "/tasks",
                json={"title": "New task", "description": "desc"},
                headers=auth_headers(client),
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == task.title
        assert data["status"] == "pending"

    def test_requires_auth(self, client):
        resp = client.post("/tasks", json={"title": "t"})
        assert resp.status_code == 401

    def test_requires_task_create_permission(self, client):
        resp = client.post(
            "/tasks",
            json={"title": "t"},
            headers=auth_headers(client, permissions=["task:read"]),
        )
        assert resp.status_code == 403

    def test_creates_task_without_description(self, client):
        task = _make_task()
        task.description = None
        with patch("app.routes.tasks.svc.create_task", new_callable=AsyncMock, return_value=task):
            resp = client.post(
                "/tasks",
                json={"title": "Minimal"},
                headers=auth_headers(client),
            )
        assert resp.status_code == 201
        assert resp.json()["description"] is None


# ---------------------------------------------------------------------------
# GET /tasks
# ---------------------------------------------------------------------------


class TestListTasks:
    def test_returns_all_tasks_for_non_viewer(self, client):
        tasks = [_make_task(), _make_task()]
        with patch("app.routes.tasks.svc.list_tasks", new_callable=AsyncMock, return_value=tasks):
            resp = client.get(
                "/tasks",
                headers=auth_headers(client, roles=["admin"]),
            )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_viewer_filters_by_owner(self, client):
        user_id = str(uuid.uuid4())
        viewer_task = _make_task(owner_id=uuid.UUID(user_id))
        with patch(
            "app.routes.tasks.svc.list_tasks", new_callable=AsyncMock, return_value=[viewer_task]
        ) as mock_list:
            resp = client.get(
                "/tasks",
                headers=auth_headers(
                    client,
                    roles=["viewer"],
                    permissions=["task:read"],
                    user_id=user_id,
                ),
            )
        assert resp.status_code == 200
        # Verify the service was called with owner_filter = the viewer's user_id
        called_kwargs = mock_list.call_args
        assert called_kwargs.kwargs["owner_filter"] == uuid.UUID(user_id)

    def test_editor_role_does_not_filter(self, client):
        tasks = [_make_task(), _make_task()]
        with patch(
            "app.routes.tasks.svc.list_tasks", new_callable=AsyncMock, return_value=tasks
        ) as mock_list:
            resp = client.get(
                "/tasks",
                headers=auth_headers(client, roles=["editor"]),
            )
        assert resp.status_code == 200
        called_kwargs = mock_list.call_args
        assert called_kwargs.kwargs["owner_filter"] is None

    def test_requires_task_read_permission(self, client):
        resp = client.get(
            "/tasks",
            headers=auth_headers(client, permissions=["task:create"]),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}
# ---------------------------------------------------------------------------


class TestGetTask:
    def test_returns_task(self, client):
        task = _make_task()
        with patch("app.routes.tasks.svc.get_task", new_callable=AsyncMock, return_value=task):
            resp = client.get(
                f"/tasks/{task.id}",
                headers=auth_headers(client),
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(task.id)

    def test_not_found(self, client):
        from fastapi import HTTPException

        with patch(
            "app.routes.tasks.svc.get_task",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=404, detail="Task not found"),
        ):
            resp = client.get(
                f"/tasks/{uuid.uuid4()}",
                headers=auth_headers(client),
            )
        assert resp.status_code == 404

    def test_requires_task_read_permission(self, client):
        resp = client.get(
            f"/tasks/{uuid.uuid4()}",
            headers=auth_headers(client, permissions=["task:create"]),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /tasks/{task_id}
# ---------------------------------------------------------------------------


class TestUpdateTask:
    def test_updates_task(self, client):
        task = _make_task(status=TaskStatus.in_progress)
        with patch("app.routes.tasks.svc.update_task", new_callable=AsyncMock, return_value=task):
            resp = client.patch(
                f"/tasks/{task.id}",
                json={"status": "in_progress"},
                headers=auth_headers(client),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    def test_not_found(self, client):
        from fastapi import HTTPException

        with patch(
            "app.routes.tasks.svc.update_task",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=404, detail="Task not found"),
        ):
            resp = client.patch(
                f"/tasks/{uuid.uuid4()}",
                json={"title": "x"},
                headers=auth_headers(client),
            )
        assert resp.status_code == 404

    def test_requires_task_update_permission(self, client):
        resp = client.patch(
            f"/tasks/{uuid.uuid4()}",
            json={"title": "x"},
            headers=auth_headers(client, permissions=["task:read"]),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}
# ---------------------------------------------------------------------------


class TestDeleteTask:
    def test_admin_can_delete(self, client):
        with patch(
            "app.routes.tasks.svc.delete_task", new_callable=AsyncMock, return_value=None
        ):
            resp = client.delete(
                f"/tasks/{uuid.uuid4()}",
                headers=auth_headers(
                    client,
                    roles=["admin"],
                    permissions=["task:delete"],
                ),
            )
        assert resp.status_code == 204

    def test_non_admin_cannot_delete(self, client):
        from fastapi import HTTPException

        with patch(
            "app.routes.tasks.svc.delete_task",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=403, detail="Admin role required"),
        ):
            resp = client.delete(
                f"/tasks/{uuid.uuid4()}",
                headers=auth_headers(
                    client,
                    roles=["editor"],
                    permissions=["task:delete"],
                ),
            )
        assert resp.status_code == 403
        assert "Admin" in resp.json()["detail"]

    def test_not_found(self, client):
        from fastapi import HTTPException

        with patch(
            "app.routes.tasks.svc.delete_task",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=404, detail="Task not found"),
        ):
            resp = client.delete(
                f"/tasks/{uuid.uuid4()}",
                headers=auth_headers(client, roles=["admin"], permissions=["task:delete"]),
            )
        assert resp.status_code == 404

    def test_requires_task_delete_permission(self, client):
        resp = client.delete(
            f"/tasks/{uuid.uuid4()}",
            headers=auth_headers(client, permissions=["task:read"]),
        )
        assert resp.status_code == 403
