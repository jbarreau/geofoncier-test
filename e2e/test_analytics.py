"""
Analytics-service end-to-end tests.

Permission mapping (from scripts/seed.py):
  viewer role: task:read, analytics:read
  admin role:  task:*, analytics:read, analytics:admin, users:manage

  viewer_token  → has analytics:read  → can access /summary and /overdue
  admin_token   → has analytics:read + analytics:admin → can access /by-user
  user_token    → has task:* but NOT analytics:* → blocked on all analytics routes

The `created_tasks` fixture (session-scoped) creates 5 tasks via the task-service API
before these tests run, ensuring the analytics endpoints return meaningful data.
"""

import httpx
import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAnalyticsSummary:
    """GET /analytics/summary — requires analytics:read"""

    async def test_viewer_can_get_summary(
        self,
        analytics_client: httpx.AsyncClient,
        viewer_token: str,
        created_tasks: list,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/summary", headers=_auth(viewer_token)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "by_status" in body
        assert isinstance(body["total"], int)
        assert body["total"] >= len(created_tasks)

    async def test_admin_can_get_summary(
        self,
        analytics_client: httpx.AsyncClient,
        admin_token: str,
        created_tasks: list,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/summary", headers=_auth(admin_token)
        )
        assert resp.status_code == 200

    async def test_summary_by_status_structure(
        self,
        analytics_client: httpx.AsyncClient,
        viewer_token: str,
        created_tasks: list,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/summary", headers=_auth(viewer_token)
        )
        body = resp.json()
        for entry in body["by_status"]:
            assert "status" in entry
            assert "count" in entry
            assert isinstance(entry["count"], int)
            assert entry["count"] >= 1

    async def test_user_without_analytics_read_gets_403(
        self,
        analytics_client: httpx.AsyncClient,
        user_token: str,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/summary", headers=_auth(user_token)
        )
        assert resp.status_code == 403

    async def test_unauthenticated_gets_401(
        self, analytics_client: httpx.AsyncClient
    ) -> None:
        resp = await analytics_client.get("/analytics/summary")
        assert resp.status_code == 401


class TestAnalyticsOverdue:
    """GET /analytics/overdue — requires analytics:read"""

    async def test_viewer_can_get_overdue(
        self,
        analytics_client: httpx.AsyncClient,
        viewer_token: str,
        created_tasks: list,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/overdue", headers=_auth(viewer_token)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "count" in body
        assert "tasks" in body
        # created_tasks fixture inserts 2 overdue tasks (doing + past due_date)
        assert body["count"] >= 2

    async def test_overdue_task_structure(
        self,
        analytics_client: httpx.AsyncClient,
        viewer_token: str,
        created_tasks: list,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/overdue", headers=_auth(viewer_token)
        )
        body = resp.json()
        assert body["count"] >= 1
        task = body["tasks"][0]
        for field in ("id", "title", "status", "owner_id", "due_date"):
            assert field in task

    async def test_overdue_excludes_done_tasks(
        self,
        analytics_client: httpx.AsyncClient,
        viewer_token: str,
        created_tasks: list,
    ) -> None:
        """Tasks with status=done must not appear in overdue list, even if past due."""
        resp = await analytics_client.get(
            "/analytics/overdue", headers=_auth(viewer_token)
        )
        body = resp.json()
        for task in body["tasks"]:
            assert task["status"] != "done"

    async def test_user_without_analytics_read_gets_403(
        self,
        analytics_client: httpx.AsyncClient,
        user_token: str,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/overdue", headers=_auth(user_token)
        )
        assert resp.status_code == 403

    async def test_unauthenticated_gets_401(
        self, analytics_client: httpx.AsyncClient
    ) -> None:
        resp = await analytics_client.get("/analytics/overdue")
        assert resp.status_code == 401


class TestAnalyticsByUser:
    """GET /analytics/by-user — requires analytics:admin"""

    async def test_admin_can_get_by_user(
        self,
        analytics_client: httpx.AsyncClient,
        admin_token: str,
        created_tasks: list,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/by-user", headers=_auth(admin_token)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "by_user" in body
        assert len(body["by_user"]) >= 1
        for entry in body["by_user"]:
            assert "owner_id" in entry
            assert "count" in entry
            assert isinstance(entry["count"], int)

    async def test_viewer_with_analytics_read_gets_403(
        self,
        analytics_client: httpx.AsyncClient,
        viewer_token: str,
    ) -> None:
        """analytics:read is NOT sufficient — analytics:admin is required."""
        resp = await analytics_client.get(
            "/analytics/by-user", headers=_auth(viewer_token)
        )
        assert resp.status_code == 403

    async def test_user_gets_403(
        self,
        analytics_client: httpx.AsyncClient,
        user_token: str,
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/by-user", headers=_auth(user_token)
        )
        assert resp.status_code == 403

    async def test_unauthenticated_gets_401(
        self, analytics_client: httpx.AsyncClient
    ) -> None:
        resp = await analytics_client.get("/analytics/by-user")
        assert resp.status_code == 401
