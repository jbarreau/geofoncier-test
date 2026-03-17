"""
Cross-service integration tests.

Validates that:
1. A JWT issued by auth-service is accepted by task-service and analytics-service
   (services fetch the public key from auth-service JWKS endpoint).
2. Logging out via auth-service immediately invalidates the token on other services
   (via the shared Redis blacklist).
"""

import uuid

import httpx
import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestJWTCrossServiceTrust:
    """Token signed by auth-service must be valid on task-service and analytics-service."""

    async def test_viewer_token_accepted_by_task_service(
        self,
        task_client: httpx.AsyncClient,
        viewer_token: str,
    ) -> None:
        """GET /tasks requires task:read — viewer role has it."""
        resp = await task_client.get("/tasks", headers=_auth(viewer_token))
        assert resp.status_code == 200

    async def test_viewer_token_accepted_by_analytics_service(
        self,
        analytics_client: httpx.AsyncClient,
        viewer_token: str,
        created_tasks: list,
    ) -> None:
        """GET /analytics/summary requires analytics:read — viewer role has it."""
        resp = await analytics_client.get(
            "/analytics/summary", headers=_auth(viewer_token)
        )
        assert resp.status_code == 200

    async def test_admin_token_accepted_by_all_services(
        self,
        task_client: httpx.AsyncClient,
        analytics_client: httpx.AsyncClient,
        admin_token: str,
        created_tasks: list,
    ) -> None:
        task_resp = await task_client.get("/tasks", headers=_auth(admin_token))
        analytics_resp = await analytics_client.get(
            "/analytics/by-user", headers=_auth(admin_token)
        )
        assert task_resp.status_code == 200
        assert analytics_resp.status_code == 200


class TestLogoutRevokesTokenAcrossServices:
    """
    Revoking a token via auth-service must make it invalid on task-service
    and analytics-service via the shared Redis blacklist (key: blacklist:{jti}).
    """

    async def _register_and_login(
        self, auth_client: httpx.AsyncClient
    ) -> dict:
        """Helper: create a fresh user and return tokens."""
        email = f"e2e_revoke_{uuid.uuid4().hex[:8]}@test.local"
        reg = await auth_client.post(
            "/auth/register",
            json={"email": email, "password": "TestPass123!"},
        )
        assert reg.status_code == 201

        login = await auth_client.post(
            "/auth/login",
            json={"email": email, "password": "TestPass123!"},
        )
        assert login.status_code == 200
        return login.json()

    async def test_token_valid_on_task_service_before_logout(
        self,
        auth_client: httpx.AsyncClient,
        task_client: httpx.AsyncClient,
    ) -> None:
        tokens = await self._register_and_login(auth_client)
        resp = await task_client.get("/tasks", headers=_auth(tokens["access_token"]))
        assert resp.status_code == 200

    async def test_token_rejected_by_task_service_after_logout(
        self,
        auth_client: httpx.AsyncClient,
        task_client: httpx.AsyncClient,
    ) -> None:
        tokens = await self._register_and_login(auth_client)

        # Confirm token is valid before logout
        before = await task_client.get("/tasks", headers=_auth(tokens["access_token"]))
        assert before.status_code == 200

        # Logout via auth-service (JTI added to Redis blacklist)
        logout = await auth_client.post(
            "/auth/logout",
            json={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert logout.status_code == 204

        # Same token must now be rejected by task-service
        after = await task_client.get("/tasks", headers=_auth(tokens["access_token"]))
        assert after.status_code == 401

    async def test_token_rejected_by_analytics_service_after_logout(
        self,
        auth_client: httpx.AsyncClient,
        analytics_client: httpx.AsyncClient,
        created_tasks: list,
    ) -> None:
        """
        The viewer role gets analytics:read, so after logout the analytics
        service must reject the same token via the Redis blacklist.
        """
        # Login with the session viewer user for a fresh token pair
        from conftest import RUN_ID, TEST_PASSWORD

        viewer_email = f"e2e_viewer_{RUN_ID}@test.local"
        login = await auth_client.post(
            "/auth/login",
            json={"email": viewer_email, "password": TEST_PASSWORD},
        )
        assert login.status_code == 200
        tokens = login.json()

        # Confirm token is valid on analytics before logout
        before = await analytics_client.get(
            "/analytics/summary", headers=_auth(tokens["access_token"])
        )
        assert before.status_code == 200

        # Logout via auth-service
        logout = await auth_client.post(
            "/auth/logout",
            json={
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            },
        )
        assert logout.status_code == 204

        # Same token must now be rejected by analytics-service
        after = await analytics_client.get(
            "/analytics/summary", headers=_auth(tokens["access_token"])
        )
        assert after.status_code == 401

    async def test_malformed_token_rejected_by_task_service(
        self, task_client: httpx.AsyncClient
    ) -> None:
        resp = await task_client.get(
            "/tasks", headers={"Authorization": "Bearer not.a.valid.jwt"}
        )
        assert resp.status_code == 401

    async def test_malformed_token_rejected_by_analytics_service(
        self, analytics_client: httpx.AsyncClient
    ) -> None:
        resp = await analytics_client.get(
            "/analytics/summary",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert resp.status_code == 401
