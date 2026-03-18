"""Integration tests for the /users endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dependencies import get_current_user_permissions
from app.exceptions import (
    RoleNotFoundError,
    UserNotFoundError,
    UserRoleAlreadyAssignedError,
    UserRoleNotFoundError,
)
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_role(name: str = "viewer") -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.name = name
    r.description = None
    r.created_at = datetime.now(timezone.utc)
    r.permissions = []
    return r


def _make_user(email: str = "user@example.com") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = email
    u.is_active = True
    u.created_at = datetime.now(timezone.utc)
    u.roles = []
    return u


def _set_auth(permissions: list[str]) -> None:
    app.dependency_overrides[get_current_user_permissions] = lambda: permissions


def _clear_auth() -> None:
    app.dependency_overrides.pop(get_current_user_permissions, None)


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------


class TestListUsers:
    async def test_200_returns_list(self, client, mocker) -> None:
        user = _make_user()
        mocker.patch(
            "app.routes.users.list_users",
            AsyncMock(return_value=[user]),
        )
        _set_auth(["users:manage"])

        resp = await client.get("/users")

        _clear_auth()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["email"] == user.email

    async def test_401_without_token(self, client) -> None:
        resp = await client.get("/users")
        assert resp.status_code == 401

    async def test_403_wrong_permission(self, client, mocker) -> None:
        mocker.patch("app.routes.users.list_users", AsyncMock(return_value=[]))
        _set_auth(["tasks:read"])

        resp = await client.get("/users")

        _clear_auth()
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------


class TestGetUser:
    async def test_200_returns_user(self, client, mocker) -> None:
        user = _make_user()
        mocker.patch(
            "app.routes.users.get_user",
            AsyncMock(return_value=user),
        )
        _set_auth(["users:manage"])

        resp = await client.get(f"/users/{user.id}")

        _clear_auth()
        assert resp.status_code == 200
        assert resp.json()["email"] == user.email

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.users.get_user",
            AsyncMock(side_effect=UserNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.get(f"/users/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.get(f"/users/{uuid.uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /users/{user_id}
# ---------------------------------------------------------------------------


class TestUpdateUser:
    async def test_200_updates_user(self, client, mocker) -> None:
        user = _make_user()
        user.is_active = False
        mocker.patch(
            "app.routes.users.update_user",
            AsyncMock(return_value=user),
        )
        _set_auth(["users:manage"])

        resp = await client.put(f"/users/{user.id}", json={"is_active": False})

        _clear_auth()
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.users.update_user",
            AsyncMock(side_effect=UserNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.put(f"/users/{uuid.uuid4()}", json={"is_active": True})

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.put(f"/users/{uuid.uuid4()}", json={"is_active": True})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /users/{user_id}/roles/{role_id}
# ---------------------------------------------------------------------------


class TestAssignRole:
    async def test_200_assigns_role(self, client, mocker) -> None:
        user = _make_user()
        role = _make_role("admin")
        # Model the UserRole junction so the schema validator can traverse it
        user_role_mock = MagicMock()
        user_role_mock.role = role
        user.roles = [user_role_mock]
        mocker.patch(
            "app.routes.users.assign_role_to_user",
            AsyncMock(return_value=user),
        )
        _set_auth(["users:manage"])

        resp = await client.post(f"/users/{user.id}/roles/{role.id}")

        _clear_auth()
        assert resp.status_code == 200

    async def test_404_user_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.users.assign_role_to_user",
            AsyncMock(side_effect=UserNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post(f"/users/{uuid.uuid4()}/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_404_role_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.users.assign_role_to_user",
            AsyncMock(side_effect=RoleNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post(f"/users/{uuid.uuid4()}/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_409_already_assigned(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.users.assign_role_to_user",
            AsyncMock(side_effect=UserRoleAlreadyAssignedError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post(f"/users/{uuid.uuid4()}/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 409

    async def test_401_without_token(self, client) -> None:
        resp = await client.post(f"/users/{uuid.uuid4()}/roles/{uuid.uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}/roles/{role_id}
# ---------------------------------------------------------------------------


class TestRemoveRole:
    async def test_200_removes_role(self, client, mocker) -> None:
        user = _make_user()
        mocker.patch(
            "app.routes.users.remove_role_from_user",
            AsyncMock(return_value=user),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/users/{user.id}/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 200

    async def test_404_user_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.users.remove_role_from_user",
            AsyncMock(side_effect=UserNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/users/{uuid.uuid4()}/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_404_role_not_assigned(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.users.remove_role_from_user",
            AsyncMock(side_effect=UserRoleNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/users/{uuid.uuid4()}/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.delete(f"/users/{uuid.uuid4()}/roles/{uuid.uuid4()}")
        assert resp.status_code == 401
