"""Health check tests — all 3 services must be up and responding."""

import httpx
import pytest


class TestHealth:
    async def test_auth_service_healthy(self, auth_client: httpx.AsyncClient) -> None:
        resp = await auth_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_task_service_healthy(self, task_client: httpx.AsyncClient) -> None:
        resp = await task_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_analytics_service_healthy(
        self, analytics_client: httpx.AsyncClient
    ) -> None:
        resp = await analytics_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
