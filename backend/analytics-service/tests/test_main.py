"""Tests for app/main.py — lifespan shutdown hook."""

from unittest.mock import AsyncMock, patch

from app.main import app


class TestMainLifespan:
    async def test_lifespan_calls_cleanup_on_shutdown(self):
        """Test the lifespan context manager directly — httpx ASGITransport
        does not drive ASGI lifespan events, so we invoke the CM ourselves."""
        from app.main import lifespan

        with (
            patch("app.main.close_redis", new_callable=AsyncMock) as mock_redis,
            patch("app.main.close_db", new_callable=AsyncMock) as mock_db,
        ):
            async with lifespan(app):
                pass  # simulate startup → request handling → shutdown
            mock_redis.assert_awaited_once()
            mock_db.assert_awaited_once()
