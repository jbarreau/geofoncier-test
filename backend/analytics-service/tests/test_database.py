"""Tests for app/database.py (singleton engine and session factory)."""

from unittest.mock import AsyncMock, MagicMock, patch


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
