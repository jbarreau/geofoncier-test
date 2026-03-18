"""Unit tests for user_service.py (mock_db AsyncMock)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.exceptions import (
    RoleNotFoundError,
    UserNotFoundError,
    UserRoleAlreadyAssignedError,
    UserRoleNotFoundError,
)
from app.services.user_service import (
    assign_role_to_user,
    get_user,
    list_users,
    remove_role_from_user,
    update_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(email: str = "user@example.com") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = email
    u.is_active = True
    u.roles = []
    return u


def _make_role(name: str = "viewer") -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.name = name
    r.permissions = []
    return r


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = [value] if value else []
    return result


def _scalars_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_returns_users(self, mock_db) -> None:
        user = _make_user()
        mock_db.execute = AsyncMock(return_value=_scalars_result([user]))

        result = await list_users(mock_db)

        assert result == [user]

    async def test_returns_empty(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalars_result([]))

        result = await list_users(mock_db)

        assert result == []


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    async def test_returns_user_when_found(self, mock_db) -> None:
        user = _make_user()
        mock_db.execute = AsyncMock(return_value=_scalar_result(user))

        result = await get_user(mock_db, user.id)

        assert result is user

    async def test_raises_404_when_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(UserNotFoundError):
            await get_user(mock_db, uuid.uuid4())


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


class TestUpdateUser:
    async def test_updates_is_active(self, mock_db) -> None:
        user = _make_user()
        mock_db.execute = AsyncMock(return_value=_scalar_result(user))
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        result = await update_user(mock_db, user.id, is_active=False)

        assert user.is_active is False
        mock_db.commit.assert_awaited()

    async def test_raises_404_when_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(UserNotFoundError):
            await update_user(mock_db, uuid.uuid4(), is_active=True)


# ---------------------------------------------------------------------------
# assign_role_to_user
# ---------------------------------------------------------------------------


class TestAssignRoleToUser:
    async def test_assigns_role_successfully(self, mock_db) -> None:
        user = _make_user()
        role = _make_role()

        # user exists, role exists, no existing assignment, then reload user
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(user),  # user check
                _scalar_result(role),  # role check
                _scalar_result(None),  # existing check
                _scalar_result(user),  # reload
            ]
        )
        mock_db.commit = AsyncMock()

        result = await assign_role_to_user(mock_db, user.id, role.id)

        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    async def test_raises_404_when_user_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(UserNotFoundError):
            await assign_role_to_user(mock_db, uuid.uuid4(), uuid.uuid4())

    async def test_raises_404_when_role_not_found(self, mock_db) -> None:
        user = _make_user()
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(user),  # user exists
                _scalar_result(None),  # role not found
            ]
        )

        with pytest.raises(RoleNotFoundError):
            await assign_role_to_user(mock_db, user.id, uuid.uuid4())

    async def test_raises_409_when_already_assigned(self, mock_db) -> None:
        user = _make_user()
        role = _make_role()
        existing = MagicMock()

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(user),
                _scalar_result(role),
                _scalar_result(existing),  # already assigned
            ]
        )

        with pytest.raises(UserRoleAlreadyAssignedError):
            await assign_role_to_user(mock_db, user.id, role.id)


# ---------------------------------------------------------------------------
# remove_role_from_user
# ---------------------------------------------------------------------------


class TestRemoveRoleFromUser:
    async def test_removes_role_successfully(self, mock_db) -> None:
        user = _make_user()
        user_role = MagicMock()

        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(user),  # user check
                _scalar_result(user_role),  # find assignment
                _scalar_result(user),  # reload
            ]
        )
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await remove_role_from_user(mock_db, user.id, uuid.uuid4())

        mock_db.delete.assert_awaited_with(user_role)
        mock_db.commit.assert_awaited()

    async def test_raises_404_when_user_not_found(self, mock_db) -> None:
        mock_db.execute = AsyncMock(return_value=_scalar_result(None))

        with pytest.raises(UserNotFoundError):
            await remove_role_from_user(mock_db, uuid.uuid4(), uuid.uuid4())

    async def test_raises_404_when_assignment_not_found(self, mock_db) -> None:
        user = _make_user()
        mock_db.execute = AsyncMock(
            side_effect=[
                _scalar_result(user),  # user exists
                _scalar_result(None),  # assignment not found
            ]
        )

        with pytest.raises(UserRoleNotFoundError):
            await remove_role_from_user(mock_db, user.id, uuid.uuid4())
