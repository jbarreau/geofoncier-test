"""Tests for infrastructure modules: config, database, redis_client, middleware, main.

Focuses on paths not exercised by test_analytics.py (shutdown hooks, singleton
re-use, alternative config branches, invalid-payload edge cases …).
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.redis_client import get_redis

# ---------------------------------------------------------------------------
# Helpers (duplicated locally to keep tests self-contained)
# ---------------------------------------------------------------------------

USER_ID = str(uuid.uuid4())


def make_token(
    private_key: str, *, sub: str = USER_ID, include_sub: bool = True
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict = {
        "email": "u@example.com",
        "roles": [],
        "permissions": [],
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    if include_sub:
        payload["sub"] = sub
    return jwt.encode(payload, private_key, algorithm="RS256")


class FakeRedis:
    async def get(self, _key: str):
        return None


# ---------------------------------------------------------------------------
# config.py
# ---------------------------------------------------------------------------


class TestConfig:
    def test_public_key_content_from_inline(self, rsa_key_pair, monkeypatch):
        from app import config

        monkeypatch.setattr(
            config.settings, "jwt_public_key", rsa_key_pair["public_key"]
        )
        monkeypatch.setattr(config.settings, "jwt_public_key_path", "")
        assert config.settings.public_key_content == rsa_key_pair["public_key"]

    def test_public_key_content_from_file(self, rsa_key_pair, tmp_path, monkeypatch):
        from app import config

        key_file = tmp_path / "public.pem"
        key_file.write_text(rsa_key_pair["public_key"])

        monkeypatch.setattr(config.settings, "jwt_public_key", "")
        monkeypatch.setattr(config.settings, "jwt_public_key_path", str(key_file))
        assert config.settings.public_key_content == rsa_key_pair["public_key"]

    def test_public_key_content_raises_when_not_configured(self, monkeypatch):
        from app import config

        monkeypatch.setattr(config.settings, "jwt_public_key", "")
        monkeypatch.setattr(config.settings, "jwt_public_key_path", "")
        with pytest.raises(ValueError, match="No JWT public key configured"):
            _ = config.settings.public_key_content


# ---------------------------------------------------------------------------
# redis_client.py
# ---------------------------------------------------------------------------


class TestRedisClient:
    async def test_get_redis_returns_singleton(self, monkeypatch):
        import app.redis_client as rc

        monkeypatch.setattr(rc, "_client", None)
        fake = MagicMock()
        with patch("app.redis_client.aioredis.from_url", return_value=fake):
            r1 = await rc.get_redis()
            r2 = await rc.get_redis()
        assert r1 is r2 is fake
        # Cleanup
        monkeypatch.setattr(rc, "_client", None)

    async def test_close_redis_closes_and_nones_client(self, monkeypatch):
        import app.redis_client as rc

        fake = AsyncMock()
        monkeypatch.setattr(rc, "_client", fake)
        await rc.close_redis()
        fake.aclose.assert_awaited_once()
        assert rc._client is None

    async def test_close_redis_noop_when_no_client(self, monkeypatch):
        import app.redis_client as rc

        monkeypatch.setattr(rc, "_client", None)
        # Should not raise
        await rc.close_redis()


# ---------------------------------------------------------------------------
# database.py
# ---------------------------------------------------------------------------


class TestDatabase:
    def test_get_engine_returns_singleton(self, monkeypatch):
        import app.database as db

        monkeypatch.setattr(db, "_engine", None)
        monkeypatch.setattr(db, "_session_factory", None)
        monkeypatch.setattr(
            "app.database.settings", MagicMock(database_url="sqlite+aiosqlite://")
        )

        with patch(
            "app.database.create_async_engine", return_value=MagicMock()
        ) as mock_create:
            e1 = db._get_engine()
            e2 = db._get_engine()
        assert e1 is e2
        mock_create.assert_called_once()
        monkeypatch.setattr(db, "_engine", None)
        monkeypatch.setattr(db, "_session_factory", None)

    def test_get_session_factory_returns_singleton(self, monkeypatch):
        import app.database as db

        fake_engine = MagicMock()
        fake_factory = MagicMock()
        monkeypatch.setattr(db, "_engine", fake_engine)
        monkeypatch.setattr(db, "_session_factory", None)

        with patch(
            "app.database.async_sessionmaker", return_value=fake_factory
        ) as mock_sm:
            f1 = db._get_session_factory()
            f2 = db._get_session_factory()
        assert f1 is f2 is fake_factory
        mock_sm.assert_called_once()
        monkeypatch.setattr(db, "_session_factory", None)

    async def test_close_db_disposes_engine_and_resets(self, monkeypatch):
        import app.database as db

        fake_engine = AsyncMock()
        monkeypatch.setattr(db, "_engine", fake_engine)
        monkeypatch.setattr(db, "_session_factory", MagicMock())
        await db.close_db()
        fake_engine.dispose.assert_awaited_once()
        assert db._engine is None
        assert db._session_factory is None

    async def test_close_db_noop_when_no_engine(self, monkeypatch):
        import app.database as db

        monkeypatch.setattr(db, "_engine", None)
        # Should not raise
        await db.close_db()

    async def test_get_db_yields_session(self, monkeypatch):
        import app.database as db

        fake_session = AsyncMock()
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=False)
        fake_factory = MagicMock(return_value=fake_session)
        monkeypatch.setattr(db, "_session_factory", fake_factory)
        monkeypatch.setattr(db, "_engine", MagicMock())

        collected = []
        async for session in db.get_db():
            collected.append(session)
        assert collected == [fake_session]


# ---------------------------------------------------------------------------
# middleware/jwt.py — missing-payload edge cases
# ---------------------------------------------------------------------------


class TestJWTMiddlewareEdgeCases:
    async def test_missing_sub_returns_401(self, rsa_key_pair):
        """Token without 'sub' claim → invalid payload."""
        token = make_token(rsa_key_pair["private_key"], include_sub=False)
        app.dependency_overrides[get_redis] = lambda: FakeRedis()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token payload"

    async def test_invalid_sub_uuid_returns_401(self, rsa_key_pair):
        """'sub' is present but not a valid UUID."""
        token = make_token(rsa_key_pair["private_key"], sub="not-a-uuid")
        app.dependency_overrides[get_redis] = lambda: FakeRedis()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token payload"

    async def test_wrong_signature_returns_401(self, rsa_key_pair):
        """Token signed with a different private key."""
        from cryptography.hazmat.primitives.asymmetric import rsa as _rsa

        other_key = _rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_private_pem = other_key.private_bytes(
            encoding=__import__(
                "cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]
            ).Encoding.PEM,
            format=__import__(
                "cryptography.hazmat.primitives.serialization",
                fromlist=["PrivateFormat"],
            ).PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=__import__(
                "cryptography.hazmat.primitives.serialization",
                fromlist=["NoEncryption"],
            ).NoEncryption(),
        ).decode()

        token = make_token(other_private_pem)
        app.dependency_overrides[get_redis] = lambda: FakeRedis()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/analytics/summary", headers={"Authorization": f"Bearer {token}"}
            )
        app.dependency_overrides.clear()
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid token"


# ---------------------------------------------------------------------------
# main.py — lifespan shutdown
# ---------------------------------------------------------------------------


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
