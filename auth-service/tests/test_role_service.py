"""Unit tests for role_service.py (mock_db AsyncMock)."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions import (
    PermissionNotFoundError,
    RoleNameConflictError,
    RoleNotFoundError,
    RolePermissionAlreadyAssignedError,
    RolePermissionNotFoundError,
)
from app.services.role_service import (
    assign_permission_to_role,
    create_role,
    delete_role,
    get_role,
    list_roles,
    remove_permission_from_role,
    update_role,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_role(name: str = "viewer") -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.name = name
    r.description = None
    r.permissions = []
    return r


def _make_permission(name: str = "tasks:read") -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.name = name
    return p


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


# ---------------------------------------------------------------------------
# list_roles
# ---------------------------------------------------------------------------


class TestListRoles:
    async def test_returns_roles(self, mock_db) -> None:
        role = _make_role()
        mock_db.execute = AsyncMock(return_value=_scalars_result([role]))

        result = await list_roles(mock_db)

        assert result == [role]

    async def test_returns_empty(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalars_result([]))

        result = await list_roles(mock_db)

        assert result == []


# ---------------------------------------------------------------------------
# get_role
# ---------------------------------------------------------------------------


class TestGetRole:
    async def test_returns_role_when_found(self, mock_db) -> None:
        role = _make_role()
        mock_db.execute = AsyncMock(return_value=_scalar_result(role))

        result = await get_role(mock_db, role.id)

        assert result is role

    async def test_raises_404_when_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(RoleNotFoundError):
            await get_role(mock_db, uuid.uuid4())


# ---------------------------------------------------------------------------
# create_role
# ---------------------------------------------------------------------------


class TestCreateRole:
    async def test_creates_role_successfully(self, mock_db) -> None:
        role = _make_role("admin")
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_scalar_result(role))

        result = await create_role(mock_db, "admin", None)

        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    async def test_raises_409_on_duplicate_name(self, mock_db) -> None:
        mock_db.commit = AsyncMock(side_effect=IntegrityError("", {}, Exception()))
        mock_db.rollback = AsyncMock()

        with pytest.raises(RoleNameConflictError):
            await create_role(mock_db, "existing", None)


# ---------------------------------------------------------------------------
# update_role
# ---------------------------------------------------------------------------


class TestUpdateRole:
    async def test_updates_name(self, mock_db) -> None:
        role = _make_role("old-name")
        mock_db.execute = AsyncMock(return_value=_scalar_result(role))
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        await update_role(mock_db, role.id, name="new-name", description=None)

        assert role.name == "new-name"

    async def test_updates_description(self, mock_db) -> None:
        role = _make_role()
        mock_db.execute = AsyncMock(return_value=_scalar_result(role))
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        await update_role(mock_db, role.id, name=None, description="desc")

        assert role.description == "desc"

    async def test_raises_404_when_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(RoleNotFoundError):
            await update_role(mock_db, uuid.uuid4(), "x", None)

    async def test_raises_409_on_duplicate_name(self, mock_db) -> None:
        role = _make_role()
        mock_db.execute = AsyncMock(return_value=_scalar_result(role))
        mock_db.commit = AsyncMock(side_effect=IntegrityError("", {}, Exception()))
        mock_db.rollback = AsyncMock()

        with pytest.raises(RoleNameConflictError):
            await update_role(mock_db, role.id, "duplicate", None)


# ---------------------------------------------------------------------------
# delete_role
# ---------------------------------------------------------------------------


class TestDeleteRole:
    async def test_deletes_role(self, mock_db) -> None:
        role = _make_role()
        mock_db.execute = AsyncMock(return_value=_scalar_result(role))
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await delete_role(mock_db, role.id)

        mock_db.delete.assert_awaited_with(role)
        mock_db.commit.assert_awaited()

    async def test_raises_404_when_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(RoleNotFoundError):
            await delete_role(mock_db, uuid.uuid4())


# ---------------------------------------------------------------------------
# assign_permission_to_role
# ---------------------------------------------------------------------------


class TestAssignPermissionToRole:
    async def test_assigns_successfully(self, mock_db) -> None:
        role = _make_role()
        perm = _make_permission()

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(role),  # role check
                _scalar_result(perm),  # permission check
                _scalar_result(None),  # not yet assigned
                _scalar_result(role),  # reload
            ]
        )
        mock_db.commit = AsyncMock()

        await assign_permission_to_role(mock_db, role.id, perm.id)

        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    async def test_raises_404_when_role_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(RoleNotFoundError):
            await assign_permission_to_role(mock_db, uuid.uuid4(), uuid.uuid4())

    async def test_raises_404_when_permission_not_found(self, mock_db) -> None:
        role = _make_role()
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(role),
                _scalar_result(None),  # permission not found
            ]
        )

        with pytest.raises(PermissionNotFoundError):
            await assign_permission_to_role(mock_db, role.id, uuid.uuid4())

    async def test_raises_409_when_already_assigned(self, mock_db) -> None:
        role = _make_role()
        perm = _make_permission()
        existing = MagicMock()

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(role),
                _scalar_result(perm),
                _scalar_result(existing),  # already assigned
            ]
        )

        with pytest.raises(RolePermissionAlreadyAssignedError):
            await assign_permission_to_role(mock_db, role.id, perm.id)


# ---------------------------------------------------------------------------
# remove_permission_from_role
# ---------------------------------------------------------------------------


class TestRemovePermissionFromRole:
    async def test_removes_successfully(self, mock_db) -> None:
        role = _make_role()
        role_perm = MagicMock()

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(role),  # role check
                _scalar_result(role_perm),  # find assignment
                _scalar_result(role),  # reload
            ]
        )
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await remove_permission_from_role(mock_db, role.id, uuid.uuid4())

        mock_db.delete.assert_awaited_with(role_perm)
        mock_db.commit.assert_awaited()

    async def test_raises_404_when_role_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(RoleNotFoundError):
            await remove_permission_from_role(mock_db, uuid.uuid4(), uuid.uuid4())

    async def test_raises_404_when_assignment_not_found(self, mock_db) -> None:
        role = _make_role()
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(role),
                _scalar_result(None),  # not assigned
            ]
        )

        with pytest.raises(RolePermissionNotFoundError):
            await remove_permission_from_role(mock_db, role.id, uuid.uuid4())
