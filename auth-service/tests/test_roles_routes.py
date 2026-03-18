"""Integration tests for the /roles endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dependencies import get_current_user_permissions
from app.exceptions import (
    PermissionNotFoundError,
    RoleNameConflictError,
    RoleNotFoundError,
    RolePermissionAlreadyAssignedError,
    RolePermissionNotFoundError,
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


def _set_auth(permissions: list[str]) -> None:
    app.dependency_overrides[get_current_user_permissions] = lambda: permissions


def _clear_auth() -> None:
    app.dependency_overrides.pop(get_current_user_permissions, None)


# ---------------------------------------------------------------------------
# GET /roles
# ---------------------------------------------------------------------------


class TestListRoles:
    async def test_200_returns_list(self, client, mocker) -> None:
        role = _make_role()
        mocker.patch(
            "app.routes.roles.list_roles",
            AsyncMock(return_value=[role]),
        )
        _set_auth(["users:manage"])

        resp = await client.get("/api/roles")

        _clear_auth()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == role.name

    async def test_401_without_token(self, client) -> None:
        resp = await client.get("/api/roles")
        assert resp.status_code == 401

    async def test_403_wrong_permission(self, client, mocker) -> None:
        mocker.patch("app.routes.roles.list_roles", AsyncMock(return_value=[]))
        _set_auth(["tasks:read"])

        resp = await client.get("/api/roles")

        _clear_auth()
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /roles
# ---------------------------------------------------------------------------


class TestCreateRole:
    async def test_201_creates_role(self, client, mocker) -> None:
        role = _make_role("admin")
        mocker.patch(
            "app.routes.roles.create_role",
            AsyncMock(return_value=role),
        )
        _set_auth(["users:manage"])

        resp = await client.post("/api/roles", json={"name": "admin"})

        _clear_auth()
        assert resp.status_code == 201
        assert resp.json()["name"] == "admin"

    async def test_409_duplicate_name(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.create_role",
            AsyncMock(side_effect=RoleNameConflictError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post("/api/roles", json={"name": "viewer"})

        _clear_auth()
        assert resp.status_code == 409

    async def test_422_missing_name(self, client) -> None:
        _set_auth(["users:manage"])

        resp = await client.post("/api/roles", json={"description": "No name"})

        _clear_auth()
        assert resp.status_code == 422

    async def test_401_without_token(self, client) -> None:
        resp = await client.post("/api/roles", json={"name": "test"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /roles/{role_id}
# ---------------------------------------------------------------------------


class TestGetRole:
    async def test_200_returns_role(self, client, mocker) -> None:
        role = _make_role()
        mocker.patch(
            "app.routes.roles.get_role",
            AsyncMock(return_value=role),
        )
        _set_auth(["users:manage"])

        resp = await client.get(f"/api/roles/{role.id}")

        _clear_auth()
        assert resp.status_code == 200
        assert resp.json()["name"] == role.name

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.get_role",
            AsyncMock(side_effect=RoleNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.get(f"/api/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.get(f"/api/roles/{uuid.uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /roles/{role_id}
# ---------------------------------------------------------------------------


class TestUpdateRole:
    async def test_200_updates_role(self, client, mocker) -> None:
        role = _make_role("updated")
        mocker.patch(
            "app.routes.roles.update_role",
            AsyncMock(return_value=role),
        )
        _set_auth(["users:manage"])

        resp = await client.put(f"/api/roles/{role.id}", json={"name": "updated"})

        _clear_auth()
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated"

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.update_role",
            AsyncMock(side_effect=RoleNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.put(f"/api/roles/{uuid.uuid4()}", json={"name": "x"})

        _clear_auth()
        assert resp.status_code == 404

    async def test_409_duplicate_name(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.update_role",
            AsyncMock(side_effect=RoleNameConflictError()),
        )
        _set_auth(["users:manage"])

        resp = await client.put(f"/api/roles/{uuid.uuid4()}", json={"name": "viewer"})

        _clear_auth()
        assert resp.status_code == 409

    async def test_401_without_token(self, client) -> None:
        resp = await client.put(f"/api/roles/{uuid.uuid4()}", json={"name": "x"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /roles/{role_id}
# ---------------------------------------------------------------------------


class TestDeleteRole:
    async def test_204_deletes_role(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.delete_role",
            AsyncMock(return_value=None),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/api/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 204

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.delete_role",
            AsyncMock(side_effect=RoleNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/api/roles/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.delete(f"/api/roles/{uuid.uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /roles/{role_id}/permissions/{permission_id}
# ---------------------------------------------------------------------------


class TestAssignPermission:
    async def test_200_assigns_permission(self, client, mocker) -> None:
        role = _make_role()
        mocker.patch(
            "app.routes.roles.assign_permission_to_role",
            AsyncMock(return_value=role),
        )
        _set_auth(["users:manage"])

        resp = await client.post(f"/api/roles/{role.id}/permissions/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 200

    async def test_404_role_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.assign_permission_to_role",
            AsyncMock(side_effect=RoleNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post(
            f"/api/roles/{uuid.uuid4()}/permissions/{uuid.uuid4()}"
        )

        _clear_auth()
        assert resp.status_code == 404

    async def test_404_permission_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.assign_permission_to_role",
            AsyncMock(side_effect=PermissionNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post(
            f"/api/roles/{uuid.uuid4()}/permissions/{uuid.uuid4()}"
        )

        _clear_auth()
        assert resp.status_code == 404

    async def test_409_already_assigned(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.assign_permission_to_role",
            AsyncMock(side_effect=RolePermissionAlreadyAssignedError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post(
            f"/api/roles/{uuid.uuid4()}/permissions/{uuid.uuid4()}"
        )

        _clear_auth()
        assert resp.status_code == 409

    async def test_401_without_token(self, client) -> None:
        resp = await client.post(
            f"/api/roles/{uuid.uuid4()}/permissions/{uuid.uuid4()}"
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /roles/{role_id}/permissions/{permission_id}
# ---------------------------------------------------------------------------


class TestRemovePermission:
    async def test_200_removes_permission(self, client, mocker) -> None:
        role = _make_role()
        mocker.patch(
            "app.routes.roles.remove_permission_from_role",
            AsyncMock(return_value=role),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/api/roles/{role.id}/permissions/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 200

    async def test_404_role_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.remove_permission_from_role",
            AsyncMock(side_effect=RoleNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(
            f"/api/roles/{uuid.uuid4()}/permissions/{uuid.uuid4()}"
        )

        _clear_auth()
        assert resp.status_code == 404

    async def test_404_not_assigned(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.roles.remove_permission_from_role",
            AsyncMock(side_effect=RolePermissionNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(
            f"/api/roles/{uuid.uuid4()}/permissions/{uuid.uuid4()}"
        )

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.delete(
            f"/api/roles/{uuid.uuid4()}/permissions/{uuid.uuid4()}"
        )
        assert resp.status_code == 401
