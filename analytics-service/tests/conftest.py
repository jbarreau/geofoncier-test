import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from geofoncier_shared.redis.redis_client import get_redis

from .helpers import FakeRedis

pytest_plugins = ["geofoncier_shared.testing"]


@pytest.fixture(autouse=True)
def patch_jwt_env(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("JWT_PUBLIC_KEY", rsa_key_pair["public_key"])
    monkeypatch.delenv("JWT_PUBLIC_KEY_PATH", raising=False)


@pytest.fixture
async def client():
    app.dependency_overrides[get_redis] = lambda: FakeRedis()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
