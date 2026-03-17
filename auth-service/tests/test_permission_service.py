"""Unit tests for app/services/permission_service.py.

Uses the mock_db AsyncMock fixture from conftest.py.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions import PermissionNameConflictError, PermissionNotFoundError
from app.services.permission_service import (
    create_permission,
    delete_permission,
    get_permission,
    list_permissions,
    update_permission,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_permission(name: str = "tasks:read", description: str | None = None) -> MagicMock:
    perm = MagicMock()
    perm.id = uuid.uuid4()
    perm.name = name
    perm.description = description
    perm.created_at = datetime.now(timezone.utc)
    return perm


def _scalars_result(items: list) -> MagicMock:
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


def _scalar_one_or_none_result(value) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# ---------------------------------------------------------------------------
# list_permissions
# ---------------------------------------------------------------------------


class TestListPermissions:
    async def test_returns_all_permissions(self, mock_db) -> None:
        perm_a = _make_permission("analytics:read")
        perm_b = _make_permission("tasks:read")
        mock_db.execute.return_value = _scalars_result([perm_a, perm_b])

        result = await list_permissions(mock_db)

        assert len(result) == 2
        assert result[0] is perm_a
        assert result[1] is perm_b

    async def test_empty_returns_empty_list(self, mock_db) -> None:
        mock_db.execute.return_value = _scalars_result([])

        result = await list_permissions(mock_db)

        assert result == []


# ---------------------------------------------------------------------------
# get_permission
# ---------------------------------------------------------------------------


class TestGetPermission:
    async def test_found_returns_permission(self, mock_db) -> None:
        perm = _make_permission("users:manage")
        mock_db.execute.return_value = _scalar_one_or_none_result(perm)

        result = await get_permission(mock_db, perm.id)

        assert result is perm

    async def test_not_found_raises_404(self, mock_db) -> None:
        mock_db.execute.return_value = _scalar_one_or_none_result(None)

        with pytest.raises(PermissionNotFoundError):
            await get_permission(mock_db, uuid.uuid4())


# ---------------------------------------------------------------------------
# create_permission
# ---------------------------------------------------------------------------


class TestCreatePermission:
    async def test_success_creates_and_returns(self, mock_db) -> None:
        async def set_defaults(perm):
            perm.id = uuid.uuid4()
            perm.created_at = datetime.now(timezone.utc)

        mock_db.refresh.side_effect = set_defaults

        result = await create_permission(mock_db, "users:manage", "Manage users")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.name == "users:manage"
        assert result.description == "Manage users"

    async def test_success_without_description(self, mock_db) -> None:
        async def set_defaults(perm):
            perm.id = uuid.uuid4()
            perm.created_at = datetime.now(timezone.utc)

        mock_db.refresh.side_effect = set_defaults

        result = await create_permission(mock_db, "tasks:read", None)

        assert result.name == "tasks:read"
        assert result.description is None

    async def test_duplicate_name_raises_409(self, mock_db) -> None:
        mock_db.commit.side_effect = IntegrityError("", {}, Exception())

        with pytest.raises(PermissionNameConflictError):
            await create_permission(mock_db, "tasks:read", None)

        mock_db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# update_permission
# ---------------------------------------------------------------------------


class TestUpdatePermission:
    async def test_name_update_only(self, mock_db) -> None:
        perm = _make_permission("old:name")
        mock_db.execute.return_value = _scalar_one_or_none_result(perm)

        async def noop_refresh(p):
            pass

        mock_db.refresh.side_effect = noop_refresh

        result = await update_permission(mock_db, perm.id, "new:name", None)

        assert result.name == "new:name"
        mock_db.commit.assert_called_once()

    async def test_description_update_only(self, mock_db) -> None:
        perm = _make_permission("tasks:read", "old desc")
        mock_db.execute.return_value = _scalar_one_or_none_result(perm)

        async def noop_refresh(p):
            pass

        mock_db.refresh.side_effect = noop_refresh

        result = await update_permission(mock_db, perm.id, None, "new desc")

        assert result.description == "new desc"
        assert result.name == "tasks:read"

    async def test_both_fields_update(self, mock_db) -> None:
        perm = _make_permission("old:name", "old desc")
        mock_db.execute.return_value = _scalar_one_or_none_result(perm)

        async def noop_refresh(p):
            pass

        mock_db.refresh.side_effect = noop_refresh

        result = await update_permission(mock_db, perm.id, "new:name", "new desc")

        assert result.name == "new:name"
        assert result.description == "new desc"

    async def test_not_found_raises_404(self, mock_db) -> None:
        mock_db.execute.return_value = _scalar_one_or_none_result(None)

        with pytest.raises(PermissionNotFoundError):
            await update_permission(mock_db, uuid.uuid4(), "name", None)

    async def test_duplicate_name_raises_409(self, mock_db) -> None:
        perm = _make_permission("tasks:read")
        mock_db.execute.return_value = _scalar_one_or_none_result(perm)
        mock_db.commit.side_effect = IntegrityError("", {}, Exception())

        with pytest.raises(PermissionNameConflictError):
            await update_permission(mock_db, perm.id, "tasks:write", None)

        mock_db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# delete_permission
# ---------------------------------------------------------------------------


class TestDeletePermission:
    async def test_success_calls_delete_and_commit(self, mock_db) -> None:
        perm = _make_permission("tasks:read")
        mock_db.execute.return_value = _scalar_one_or_none_result(perm)

        await delete_permission(mock_db, perm.id)

        mock_db.delete.assert_called_once_with(perm)
        mock_db.commit.assert_called_once()

    async def test_not_found_raises_404(self, mock_db) -> None:
        mock_db.execute.return_value = _scalar_one_or_none_result(None)

        with pytest.raises(PermissionNotFoundError):
            await delete_permission(mock_db, uuid.uuid4())
