"""Tests for app/main.py (health, lifespan hooks)."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


class TestMain:
    def test_health(self):
        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_shutdown_closes_redis(self):
        import geofoncier_shared.redis.redis_client as rc

        mock_client = AsyncMock()
        rc._client = mock_client
        from app.main import shutdown

        await shutdown()
        mock_client.aclose.assert_awaited_once()
        rc._client = None
