"""Unit tests for app/dependencies.py.

JWT decoding is patched so no real key material is needed.
The `patch_settings` fixture from conftest.py is autouse so it runs automatically.
"""

from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import get_current_user_permissions, require_permission
from app.exceptions import InsufficientPermissionsError, InvalidTokenError


# ---------------------------------------------------------------------------
# get_current_user_permissions
# ---------------------------------------------------------------------------


class TestGetCurrentUserPermissions:
    def test_missing_credentials_raises_401(self) -> None:
        with pytest.raises(InvalidTokenError):
            get_current_user_permissions(credentials=None)

    def test_invalid_token_raises_401(self) -> None:
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = "bad.token.here"

        with patch(
            "app.dependencies.decode_access_token",
            side_effect=jwt.PyJWTError("invalid"),
        ):
            with pytest.raises(InvalidTokenError):
                get_current_user_permissions(credentials=creds)

    def test_valid_token_returns_permissions(self) -> None:
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = "valid.token"

        with patch(
            "app.dependencies.decode_access_token",
            return_value={"permissions": ["users:manage", "tasks:read"]},
        ):
            result = get_current_user_permissions(credentials=creds)

        assert result == ["users:manage", "tasks:read"]

    def test_token_without_permissions_claim_returns_empty_list(self) -> None:
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = "valid.token"

        with patch(
            "app.dependencies.decode_access_token",
            return_value={"sub": "user-id", "email": "u@e.com"},
        ):
            result = get_current_user_permissions(credentials=creds)

        assert result == []


# ---------------------------------------------------------------------------
# require_permission
# ---------------------------------------------------------------------------


class TestRequirePermission:
    def test_permission_present_does_not_raise(self) -> None:
        checker = require_permission("users:manage")
        # Call the inner _check directly with injected permissions
        result = checker.__wrapped__(["users:manage", "tasks:read"]) if hasattr(checker, "__wrapped__") else None
        # Call via closure — require_permission returns a function
        inner = require_permission("users:manage")
        # The returned callable is the inner _check function
        result = inner(["users:manage"])
        assert "users:manage" in result

    def test_permission_absent_raises_403(self) -> None:
        inner = require_permission("users:manage")
        with pytest.raises(InsufficientPermissionsError):
            inner([])

    def test_wrong_permission_raises_403(self) -> None:
        inner = require_permission("users:manage")
        with pytest.raises(InsufficientPermissionsError):
            inner(["tasks:read", "tasks:write"])

    def test_returns_permissions_list_on_success(self) -> None:
        inner = require_permission("users:manage")
        perms = ["users:manage", "tasks:read"]
        result = inner(perms)
        assert result == perms
