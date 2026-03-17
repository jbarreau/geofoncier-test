from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

pytest_plugins = ["geofoncier_shared.testing"]


@pytest.fixture(autouse=True)
def patch_settings(rsa_key_pair, monkeypatch):
    """Inject the test key pair into settings so the app starts without real key files."""
    from app import config

    monkeypatch.setattr(config.settings, "jwt_private_key", rsa_key_pair["private_key"])
    monkeypatch.setattr(config.settings, "jwt_public_key", rsa_key_pair["public_key"])
    monkeypatch.setattr(config.settings, "jwt_private_key_path", "")
    monkeypatch.setattr(config.settings, "jwt_public_key_path", "")


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()  # add() is synchronous in SQLAlchemy
    return db


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest_asyncio.fixture
async def client(mock_db, mock_redis, patch_settings):
    """AsyncClient wired to the FastAPI app with DB and Redis dependencies mocked out."""
    from app.database import get_db
    from app.main import app
    from geofoncier_shared.redis.redis_client import get_redis

    async def _get_db():
        yield mock_db

    async def _get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()
