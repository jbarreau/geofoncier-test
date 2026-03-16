from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generate a throwaway RSA-2048 key pair shared across the test session."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


@pytest.fixture(autouse=True)
def patch_settings(rsa_key_pair, monkeypatch):
    """Inject the test key pair into settings so the app starts without real key files."""
    from app import config

    private_pem, public_pem = rsa_key_pair
    monkeypatch.setattr(config.settings, "jwt_private_key", private_pem)
    monkeypatch.setattr(config.settings, "jwt_public_key", public_pem)
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
    from app.redis_client import get_redis

    async def _get_db():
        yield mock_db

    async def _get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
