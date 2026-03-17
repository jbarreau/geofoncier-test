import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.redis_client import get_redis

from .helpers import FakeRedis

pytest_plugins = ["geofoncier_shared.testing"]


@pytest.fixture(autouse=True)
def patch_settings(rsa_key_pair, monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "jwt_public_key", rsa_key_pair["public_key"])
    monkeypatch.setattr(config.settings, "jwt_public_key_path", "")


@pytest.fixture
async def client():
    app.dependency_overrides[get_redis] = lambda: FakeRedis()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
