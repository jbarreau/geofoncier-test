"""Tests for geofoncier_shared.fastapi.schemas.auth (CurrentUser)."""

import uuid

from geofoncier_shared.fastapi.schemas.auth import CurrentUser


class TestCurrentUser:
    def test_valid(self):
        uid = uuid.uuid4()
        u = CurrentUser(user_id=uid, roles=["admin"], permissions=["task:create"])
        assert u.user_id == uid
        assert u.roles == ["admin"]
        assert u.permissions == ["task:create"]
