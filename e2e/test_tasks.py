"""
Task-service end-to-end tests.

Permission mapping (from scripts/seed.py after fix):
  viewer role: task:read, analytics:read
  user role:   task:create, task:read, task:update
  admin role:  task:create, task:read, task:update, task:delete, analytics:*, users:manage

Test users (session fixtures from conftest.py):
  viewer_token  — viewer role only
  user_token    — viewer + user roles
  admin_token   — viewer + admin roles
"""

import uuid

import httpx
import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestTaskCreate:
    async def test_user_can_create_task(
        self, task_client: httpx.AsyncClient, user_token: str
    ) -> None:
        resp = await task_client.post(
            "/api/tasks",
            json={"title": "My user task", "status": "todo"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "My user task"
        assert body["status"] == "todo"
        assert "id" in body
        assert "owner_id" in body

    async def test_admin_can_create_task(
        self, task_client: httpx.AsyncClient, admin_token: str
    ) -> None:
        resp = await task_client.post(
            "/api/tasks",
            json={"title": "Admin task", "status": "doing"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 201

    async def test_viewer_cannot_create_task(
        self, task_client: httpx.AsyncClient, viewer_token: str
    ) -> None:
        resp = await task_client.post(
            "/api/tasks",
            json={"title": "Viewer task"},
            headers=_auth(viewer_token),
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_create_task(
        self, task_client: httpx.AsyncClient
    ) -> None:
        resp = await task_client.post("/api/tasks", json={"title": "No auth"})
        assert resp.status_code == 401


class TestTaskRead:
    async def test_user_can_list_own_tasks(
        self, task_client: httpx.AsyncClient, user_token: str
    ) -> None:
        # Create a task first
        await task_client.post(
            "/api/tasks",
            json={"title": "List test task"},
            headers=_auth(user_token),
        )
        resp = await task_client.get("/api/tasks", headers=_auth(user_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_viewer_can_list_tasks(
        self, task_client: httpx.AsyncClient, viewer_token: str
    ) -> None:
        resp = await task_client.get("/api/tasks", headers=_auth(viewer_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_unauthenticated_cannot_list_tasks(
        self, task_client: httpx.AsyncClient
    ) -> None:
        resp = await task_client.get("/api/tasks")
        assert resp.status_code == 401

    async def test_user_can_get_own_task_by_id(
        self, task_client: httpx.AsyncClient, user_token: str
    ) -> None:
        create = await task_client.post(
            "/api/tasks",
            json={"title": "Get by id test"},
            headers=_auth(user_token),
        )
        assert create.status_code == 201
        task_id = create.json()["id"]

        resp = await task_client.get(f"/api/tasks/{task_id}", headers=_auth(user_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    async def test_get_nonexistent_task_returns_404(
        self, task_client: httpx.AsyncClient, user_token: str
    ) -> None:
        resp = await task_client.get(
            f"/api/tasks/{uuid.uuid4()}", headers=_auth(user_token)
        )
        assert resp.status_code == 404


class TestTaskUpdate:
    async def test_user_can_update_own_task(
        self, task_client: httpx.AsyncClient, user_token: str
    ) -> None:
        create = await task_client.post(
            "/api/tasks",
            json={"title": "Update me", "status": "todo"},
            headers=_auth(user_token),
        )
        task_id = create.json()["id"]

        resp = await task_client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "doing"},
            headers=_auth(user_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "doing"

    async def test_viewer_cannot_update_task(
        self, task_client: httpx.AsyncClient,
        user_token: str,
        viewer_token: str,
    ) -> None:
        create = await task_client.post(
            "/api/tasks",
            json={"title": "Viewer cannot update"},
            headers=_auth(user_token),
        )
        task_id = create.json()["id"]

        resp = await task_client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "done"},
            headers=_auth(viewer_token),
        )
        assert resp.status_code == 403


class TestTaskDelete:
    async def test_admin_can_delete_task(
        self, task_client: httpx.AsyncClient, admin_token: str
    ) -> None:
        create = await task_client.post(
            "/api/tasks",
            json={"title": "Delete me"},
            headers=_auth(admin_token),
        )
        task_id = create.json()["id"]

        resp = await task_client.delete(
            f"/api/tasks/{task_id}", headers=_auth(admin_token)
        )
        assert resp.status_code == 204

        # Confirm task is gone
        get = await task_client.get(
            f"/api/tasks/{task_id}", headers=_auth(admin_token)
        )
        assert get.status_code == 404

    async def test_user_cannot_delete_task(
        self, task_client: httpx.AsyncClient, user_token: str
    ) -> None:
        create = await task_client.post(
            "/api/tasks",
            json={"title": "User cannot delete"},
            headers=_auth(user_token),
        )
        task_id = create.json()["id"]

        resp = await task_client.delete(
            f"/api/tasks/{task_id}", headers=_auth(user_token)
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_delete_task(
        self, task_client: httpx.AsyncClient, admin_token: str
    ) -> None:
        create = await task_client.post(
            "/api/tasks",
            json={"title": "No auth delete"},
            headers=_auth(admin_token),
        )
        task_id = create.json()["id"]

        resp = await task_client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 401
