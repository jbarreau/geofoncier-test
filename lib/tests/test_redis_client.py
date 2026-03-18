from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import geofoncier_shared.redis.redis_client as rc


@pytest.fixture(autouse=True)
def reset_module_state():
    """Restore module-level globals after each test."""
    original_client = rc._client
    original_url = rc._redis_url
    yield
    rc._client = original_client
    rc._redis_url = original_url


class TestConfigure:
    def test_sets_redis_url(self):
        rc.configure("redis://myhost:6380")
        assert rc._redis_url == "redis://myhost:6380"

    def test_does_not_affect_existing_client(self):
        mock_client = MagicMock()
        rc._client = mock_client
        rc.configure("redis://other:6380")
        assert rc._client is mock_client


class TestGetRedis:
    @pytest.mark.asyncio
    async def test_creates_client_on_first_call(self):
        rc._client = None
        rc._redis_url = "redis://localhost:6379"
        mock_client = MagicMock()
        with patch("redis.asyncio.from_url", return_value=mock_client) as mock_from_url:
            client = await rc.get_redis()
        mock_from_url.assert_called_once_with(
            "redis://localhost:6379", decode_responses=True
        )
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_reuses_existing_client(self):
        mock_client = MagicMock()
        rc._client = mock_client
        with patch("redis.asyncio.from_url") as mock_from_url:
            client = await rc.get_redis()
        mock_from_url.assert_not_called()
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_uses_configured_url(self):
        rc._client = None
        rc.configure("redis://custom:9999")
        mock_client = MagicMock()
        with patch("redis.asyncio.from_url", return_value=mock_client) as mock_from_url:
            await rc.get_redis()
        mock_from_url.assert_called_once_with(
            "redis://custom:9999", decode_responses=True
        )


class TestCloseRedis:
    @pytest.mark.asyncio
    async def test_closes_and_clears_client(self):
        mock_client = AsyncMock()
        rc._client = mock_client
        await rc.close_redis()
        mock_client.aclose.assert_awaited_once()
        assert rc._client is None

    @pytest.mark.asyncio
    async def test_noop_when_no_client(self):
        rc._client = None
        await rc.close_redis()  # must not raise
        assert rc._client is None
