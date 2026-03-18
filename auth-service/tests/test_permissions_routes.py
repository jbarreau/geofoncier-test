"""Integration tests for the /permissions endpoints.

The service layer is mocked via mocker.patch.
Authentication is controlled by overriding get_current_user_permissions
in app.dependency_overrides.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dependencies import get_current_user_permissions
from app.exceptions import PermissionNameConflictError, PermissionNotFoundError
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_perm(name: str = "tasks:read") -> MagicMock:
    perm = MagicMock()
    perm.id = uuid.uuid4()
    perm.name = name
    perm.description = None
    perm.created_at = datetime.now(timezone.utc)
    return perm


def _perm_dict(perm: MagicMock) -> dict:
    return {
        "id": str(perm.id),
        "name": perm.name,
        "description": perm.description,
        "created_at": perm.created_at.isoformat(),
    }


def _set_auth(permissions: list[str]) -> None:
    """Override the auth dependency to return the given permissions."""
    app.dependency_overrides[get_current_user_permissions] = lambda: permissions


def _clear_auth() -> None:
    app.dependency_overrides.pop(get_current_user_permissions, None)


# ---------------------------------------------------------------------------
# GET /permissions
# ---------------------------------------------------------------------------


class TestListPermissions:
    async def test_200_returns_list(self, client, mocker) -> None:
        perm = _make_perm("tasks:read")
        mocker.patch(
            "app.routes.permissions.list_permissions",
            AsyncMock(return_value=[perm]),
        )
        _set_auth(["users:manage"])

        resp = await client.get("/permissions")

        _clear_auth()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "tasks:read"

    async def test_200_returns_empty_list(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.list_permissions",
            AsyncMock(return_value=[]),
        )
        _set_auth(["users:manage"])

        resp = await client.get("/permissions")

        _clear_auth()
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_401_without_token(self, client) -> None:
        resp = await client.get("/permissions")
        assert resp.status_code == 401

    async def test_403_without_manage_permission(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.list_permissions",
            AsyncMock(return_value=[]),
        )
        _set_auth(["tasks:read"])

        resp = await client.get("/permissions")

        _clear_auth()
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /permissions
# ---------------------------------------------------------------------------


class TestCreatePermission:
    async def test_201_creates_permission(self, client, mocker) -> None:
        perm = _make_perm("users:manage")
        mocker.patch(
            "app.routes.permissions.create_permission",
            AsyncMock(return_value=perm),
        )
        _set_auth(["users:manage"])

        resp = await client.post(
            "/permissions",
            json={"name": "users:manage", "description": "Manage users"},
        )

        _clear_auth()
        assert resp.status_code == 201
        assert resp.json()["name"] == "users:manage"

    async def test_409_duplicate_name(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.create_permission",
            AsyncMock(side_effect=PermissionNameConflictError()),
        )
        _set_auth(["users:manage"])

        resp = await client.post("/permissions", json={"name": "tasks:read"})

        _clear_auth()
        assert resp.status_code == 409

    async def test_422_missing_name(self, client) -> None:
        _set_auth(["users:manage"])

        resp = await client.post("/permissions", json={"description": "No name"})

        _clear_auth()
        assert resp.status_code == 422

    async def test_401_without_token(self, client) -> None:
        resp = await client.post("/permissions", json={"name": "test"})
        assert resp.status_code == 401

    async def test_403_wrong_permission(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.create_permission",
            AsyncMock(return_value=_make_perm()),
        )
        _set_auth(["tasks:read"])

        resp = await client.post("/permissions", json={"name": "test"})

        _clear_auth()
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /permissions/{id}
# ---------------------------------------------------------------------------


class TestGetPermission:
    async def test_200_returns_permission(self, client, mocker) -> None:
        perm = _make_perm("tasks:read")
        mocker.patch(
            "app.routes.permissions.get_permission",
            AsyncMock(return_value=perm),
        )
        _set_auth(["users:manage"])

        resp = await client.get(f"/permissions/{perm.id}")

        _clear_auth()
        assert resp.status_code == 200
        assert resp.json()["name"] == "tasks:read"

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.get_permission",
            AsyncMock(side_effect=PermissionNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.get(f"/permissions/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.get(f"/permissions/{uuid.uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /permissions/{id}
# ---------------------------------------------------------------------------


class TestUpdatePermission:
    async def test_200_updates_permission(self, client, mocker) -> None:
        perm = _make_perm("updated:name")
        mocker.patch(
            "app.routes.permissions.update_permission",
            AsyncMock(return_value=perm),
        )
        _set_auth(["users:manage"])

        resp = await client.put(
            f"/permissions/{perm.id}",
            json={"name": "updated:name"},
        )

        _clear_auth()
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated:name"

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.update_permission",
            AsyncMock(side_effect=PermissionNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.put(
            f"/permissions/{uuid.uuid4()}",
            json={"name": "new:name"},
        )

        _clear_auth()
        assert resp.status_code == 404

    async def test_409_duplicate_name(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.update_permission",
            AsyncMock(side_effect=PermissionNameConflictError()),
        )
        _set_auth(["users:manage"])

        resp = await client.put(
            f"/permissions/{uuid.uuid4()}",
            json={"name": "tasks:read"},
        )

        _clear_auth()
        assert resp.status_code == 409

    async def test_401_without_token(self, client) -> None:
        resp = await client.put(f"/permissions/{uuid.uuid4()}", json={"name": "x"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /permissions/{id}
# ---------------------------------------------------------------------------


class TestDeletePermission:
    async def test_204_deletes_permission(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.delete_permission",
            AsyncMock(return_value=None),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/permissions/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 204

    async def test_404_not_found(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.delete_permission",
            AsyncMock(side_effect=PermissionNotFoundError()),
        )
        _set_auth(["users:manage"])

        resp = await client.delete(f"/permissions/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 404

    async def test_401_without_token(self, client) -> None:
        resp = await client.delete(f"/permissions/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_403_wrong_permission(self, client, mocker) -> None:
        mocker.patch(
            "app.routes.permissions.delete_permission",
            AsyncMock(return_value=None),
        )
        _set_auth(["tasks:read"])

        resp = await client.delete(f"/permissions/{uuid.uuid4()}")

        _clear_auth()
        assert resp.status_code == 403
