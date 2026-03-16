"""Unit tests for the auth service layer.

DB and Redis interactions are mocked via the fixtures provided in conftest.py.
`_load_roles_and_permissions` is patched for success-path tests to avoid
re-testing the SQLAlchemy eager-loading chain (covered in its own class).
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.services.auth_service import (
    _load_roles_and_permissions,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
)
from app.services.password_service import hash_password
from app.services.token_service import create_access_token, create_refresh_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result(*, one_or_none=None, one=None) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = one_or_none
    r.scalar_one.return_value = one
    return r


# ---------------------------------------------------------------------------
# _load_roles_and_permissions
# ---------------------------------------------------------------------------


class TestLoadRolesAndPermissions:
    async def test_returns_role_and_permission_names(self, mock_db) -> None:
        perm_a = MagicMock()
        perm_a.permission.name = "users:read"
        perm_b = MagicMock()
        perm_b.permission.name = "users:write"

        role_entry = MagicMock()
        role_entry.role.name = "admin"
        role_entry.role.permissions = [perm_a, perm_b]

        mock_user = MagicMock()
        mock_user.roles = [role_entry]

        mock_db.execute.return_value = _result(one=mock_user)

        roles, permissions = await _load_roles_and_permissions(mock_db, uuid.uuid4())

        assert roles == ["admin"]
        assert set(permissions) == {"users:read", "users:write"}

    async def test_user_with_no_roles(self, mock_db) -> None:
        mock_user = MagicMock()
        mock_user.roles = []
        mock_db.execute.return_value = _result(one=mock_user)

        roles, permissions = await _load_roles_and_permissions(mock_db, uuid.uuid4())

        assert roles == []
        assert permissions == []

    async def test_deduplicates_permissions_across_roles(self, mock_db) -> None:
        shared_perm = MagicMock()
        shared_perm.permission.name = "tasks:read"

        role1 = MagicMock()
        role1.role.name = "viewer"
        role1.role.permissions = [shared_perm]

        role2 = MagicMock()
        role2.role.name = "editor"
        role2.role.permissions = [shared_perm]

        mock_user = MagicMock()
        mock_user.roles = [role1, role2]
        mock_db.execute.return_value = _result(one=mock_user)

        _, permissions = await _load_roles_and_permissions(mock_db, uuid.uuid4())

        assert permissions.count("tasks:read") == 1


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------


class TestRegisterUser:
    async def test_duplicate_email_raises(self, mock_db) -> None:
        mock_db.execute.return_value = _result(one_or_none=MagicMock())

        with pytest.raises(EmailAlreadyExistsError):
            await register_user(mock_db, "taken@example.com", "password123")

    async def test_missing_default_role_raises(self, mock_db) -> None:
        mock_db.execute.side_effect = [
            _result(one_or_none=None),  # no existing user
            _result(one_or_none=None),  # no "viewer" role
        ]

        with pytest.raises(RuntimeError, match="viewer"):
            await register_user(mock_db, "new@example.com", "password123")

    async def test_success_creates_and_returns_user(self, mock_db) -> None:
        mock_role = MagicMock()
        mock_role.id = uuid.uuid4()

        mock_db.execute.side_effect = [
            _result(one_or_none=None),  # no existing user
            _result(one_or_none=mock_role),  # viewer role exists
        ]

        async def set_server_defaults(obj: object) -> None:
            obj.id = uuid.uuid4()  # type: ignore[attr-defined]
            obj.is_active = True  # type: ignore[attr-defined]
            obj.created_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]

        mock_db.refresh.side_effect = set_server_defaults

        result = await register_user(mock_db, "alice@example.com", "password123")

        assert result.email == "alice@example.com"
        assert result.is_active is True
        mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# login_user
# ---------------------------------------------------------------------------


class TestLoginUser:
    async def test_unknown_email_raises(self, mock_db, mock_redis) -> None:
        mock_db.execute.return_value = _result(one_or_none=None)

        with pytest.raises(InvalidCredentialsError):
            await login_user(mock_db, mock_redis, "nobody@example.com", "pass")

    async def test_wrong_password_raises(self, mock_db, mock_redis) -> None:
        mock_user = MagicMock()
        mock_user.hashed_password = hash_password("correct_pass")
        mock_db.execute.return_value = _result(one_or_none=mock_user)

        with pytest.raises(InvalidCredentialsError):
            await login_user(mock_db, mock_redis, "user@example.com", "wrong_pass")

    async def test_inactive_user_raises(self, mock_db, mock_redis) -> None:
        mock_user = MagicMock()
        mock_user.hashed_password = hash_password("password")
        mock_user.is_active = False
        mock_db.execute.return_value = _result(one_or_none=mock_user)

        with pytest.raises(InactiveUserError):
            await login_user(mock_db, mock_redis, "inactive@example.com", "password")

    async def test_success_returns_token_pair(
        self, mock_db, mock_redis, mocker
    ) -> None:
        mock_user = MagicMock()
        mock_user.hashed_password = hash_password("password")
        mock_user.is_active = True
        mock_user.id = uuid.uuid4()
        mock_user.email = "user@example.com"
        mock_db.execute.return_value = _result(one_or_none=mock_user)

        mocker.patch(
            "app.services.auth_service._load_roles_and_permissions",
            AsyncMock(return_value=(["viewer"], ["tasks:read"])),
        )

        result = await login_user(mock_db, mock_redis, "user@example.com", "password")

        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"
        mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# refresh_tokens
# ---------------------------------------------------------------------------


class TestRefreshTokens:
    async def test_malformed_token_raises(self, mock_db, mock_redis) -> None:
        with pytest.raises(InvalidRefreshTokenError):
            await refresh_tokens(mock_db, mock_redis, "not-a-valid-uuid:ignored")

    async def test_token_not_in_db_raises(self, mock_db, mock_redis) -> None:
        raw, _, _, _ = create_refresh_token()
        mock_db.execute.return_value = _result(one_or_none=None)

        with pytest.raises(InvalidRefreshTokenError):
            await refresh_tokens(mock_db, mock_redis, raw)

    async def test_wrong_hash_raises(self, mock_db, mock_redis) -> None:
        raw, _, _, _ = create_refresh_token()

        mock_record = MagicMock()
        mock_record.token_hash = "wrong_hash_value"
        mock_db.execute.return_value = _result(one_or_none=mock_record)

        with pytest.raises(InvalidRefreshTokenError):
            await refresh_tokens(mock_db, mock_redis, raw)

    async def test_inactive_user_raises(self, mock_db, mock_redis) -> None:
        raw, token_hash, _, _ = create_refresh_token()

        mock_record = MagicMock()
        mock_record.token_hash = token_hash
        mock_record.user_id = uuid.uuid4()

        mock_user = MagicMock()
        mock_user.is_active = False

        mock_db.execute.side_effect = [
            _result(one_or_none=mock_record),
            _result(one=mock_user),
        ]

        with pytest.raises(InactiveUserError):
            await refresh_tokens(mock_db, mock_redis, raw)

    async def test_success_revokes_old_and_returns_new_pair(
        self, mock_db, mock_redis, mocker
    ) -> None:
        raw, token_hash, _, _ = create_refresh_token()

        mock_record = MagicMock()
        mock_record.token_hash = token_hash
        mock_record.user_id = uuid.uuid4()

        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.id = mock_record.user_id
        mock_user.email = "user@example.com"

        mock_db.execute.side_effect = [
            _result(one_or_none=mock_record),
            _result(one=mock_user),
        ]

        mocker.patch(
            "app.services.auth_service._load_roles_and_permissions",
            AsyncMock(return_value=([], [])),
        )

        result = await refresh_tokens(mock_db, mock_redis, raw)

        assert result.access_token
        assert result.refresh_token
        assert mock_record.revoked is True
        mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# logout_user
# ---------------------------------------------------------------------------


class TestLogoutUser:
    async def test_malformed_refresh_token_returns_early(
        self, mock_db, mock_redis
    ) -> None:
        token, _, _ = create_access_token(uuid.uuid4(), "u@e.com", [], [])

        await logout_user(mock_db, mock_redis, token, "no-colon-no-uuid")

        mock_db.execute.assert_not_called()

    async def test_invalid_access_token_does_not_raise(
        self, mock_db, mock_redis
    ) -> None:
        raw, _, _, _ = create_refresh_token()
        mock_db.execute.return_value = _result(one_or_none=None)

        await logout_user(mock_db, mock_redis, "garbage_access_token", raw)

    async def test_token_not_found_does_not_commit(self, mock_db, mock_redis) -> None:
        token, _, _ = create_access_token(uuid.uuid4(), "u@e.com", [], [])
        raw, _, _, _ = create_refresh_token()
        mock_db.execute.return_value = _result(one_or_none=None)

        await logout_user(mock_db, mock_redis, token, raw)

        mock_db.commit.assert_not_called()

    async def test_success_revokes_token_and_blacklists_jti(
        self, mock_db, mock_redis
    ) -> None:
        token, _, _ = create_access_token(uuid.uuid4(), "u@e.com", [], [])
        raw, token_hash, _, _ = create_refresh_token()

        mock_record = MagicMock()
        mock_record.token_hash = token_hash
        mock_db.execute.return_value = _result(one_or_none=mock_record)

        await logout_user(mock_db, mock_redis, token, raw)

        assert mock_record.revoked is True
        mock_db.commit.assert_called_once()
        mock_redis.setex.assert_called_once()
