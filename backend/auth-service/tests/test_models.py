"""Unit tests for SQLAlchemy model definitions.

Validates column names, types, constraints, foreign keys, and relationships
without requiring a live database connection.
"""

import uuid

from sqlalchemy import inspect as sa_inspect

from app.models.associations import RolePermission, UserRole
from app.models.base import Base
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User


def _col_names(model: type) -> set:
    return {c.name for c in model.__table__.columns}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_metadata_schema_is_auth(self) -> None:
        assert Base.metadata.schema == "auth"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class TestUserModel:
    def test_tablename(self) -> None:
        assert User.__tablename__ == "users"

    def test_columns(self) -> None:
        assert _col_names(User) == {
            "id",
            "email",
            "hashed_password",
            "is_active",
            "created_at",
            "updated_at",
        }

    def test_email_unique(self) -> None:
        assert User.__table__.columns["email"].unique is True

    def test_email_not_nullable(self) -> None:
        assert User.__table__.columns["email"].nullable is False

    def test_hashed_password_not_nullable(self) -> None:
        assert User.__table__.columns["hashed_password"].nullable is False

    def test_is_active_has_server_default(self) -> None:
        assert User.__table__.columns["is_active"].server_default is not None

    def test_relationships(self) -> None:
        rel_keys = {r.key for r in sa_inspect(User).relationships}
        assert {"roles", "refresh_tokens"}.issubset(rel_keys)

    def test_instantiation(self) -> None:
        user = User(
            id=uuid.uuid4(), email="alice@example.com", hashed_password="$2b$12$x"
        )
        assert user.email == "alice@example.com"


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------


class TestRoleModel:
    def test_tablename(self) -> None:
        assert Role.__tablename__ == "roles"

    def test_columns(self) -> None:
        assert _col_names(Role) == {"id", "name", "description", "created_at"}

    def test_name_unique(self) -> None:
        assert Role.__table__.columns["name"].unique is True

    def test_name_not_nullable(self) -> None:
        assert Role.__table__.columns["name"].nullable is False

    def test_description_nullable(self) -> None:
        assert Role.__table__.columns["description"].nullable is True

    def test_relationships(self) -> None:
        rel_keys = {r.key for r in sa_inspect(Role).relationships}
        assert {"users", "permissions"}.issubset(rel_keys)

    def test_instantiation(self) -> None:
        role = Role(id=uuid.uuid4(), name="admin")
        assert role.name == "admin"
        assert role.description is None


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------


class TestPermissionModel:
    def test_tablename(self) -> None:
        assert Permission.__tablename__ == "permissions"

    def test_columns(self) -> None:
        assert _col_names(Permission) == {"id", "name", "description", "created_at"}

    def test_name_unique(self) -> None:
        assert Permission.__table__.columns["name"].unique is True

    def test_name_not_nullable(self) -> None:
        assert Permission.__table__.columns["name"].nullable is False

    def test_description_nullable(self) -> None:
        assert Permission.__table__.columns["description"].nullable is True

    def test_relationships(self) -> None:
        rel_keys = {r.key for r in sa_inspect(Permission).relationships}
        assert "roles" in rel_keys

    def test_instantiation(self) -> None:
        perm = Permission(id=uuid.uuid4(), name="users:read")
        assert perm.name == "users:read"


# ---------------------------------------------------------------------------
# RefreshToken
# ---------------------------------------------------------------------------


class TestRefreshTokenModel:
    def test_tablename(self) -> None:
        assert RefreshToken.__tablename__ == "refresh_tokens"

    def test_columns(self) -> None:
        assert _col_names(RefreshToken) == {
            "id",
            "user_id",
            "token_hash",
            "revoked",
            "expires_at",
            "created_at",
        }

    def test_token_hash_unique(self) -> None:
        assert RefreshToken.__table__.columns["token_hash"].unique is True

    def test_token_hash_not_nullable(self) -> None:
        assert RefreshToken.__table__.columns["token_hash"].nullable is False

    def test_revoked_has_server_default(self) -> None:
        assert RefreshToken.__table__.columns["revoked"].server_default is not None

    def test_user_id_fk_cascade(self) -> None:
        col = RefreshToken.__table__.columns["user_id"]
        fk = next(iter(col.foreign_keys))
        assert fk.ondelete == "CASCADE"
        assert fk.target_fullname == "auth.users.id"

    def test_relationships(self) -> None:
        rel_keys = {r.key for r in sa_inspect(RefreshToken).relationships}
        assert "user" in rel_keys


# ---------------------------------------------------------------------------
# UserRole (association)
# ---------------------------------------------------------------------------


class TestUserRoleModel:
    def test_tablename(self) -> None:
        assert UserRole.__tablename__ == "user_roles"

    def test_columns(self) -> None:
        assert _col_names(UserRole) == {"user_id", "role_id", "assigned_at"}

    def test_composite_pk(self) -> None:
        pk_cols = {c.name for c in UserRole.__table__.primary_key.columns}
        assert pk_cols == {"user_id", "role_id"}

    def test_user_id_fk_cascade(self) -> None:
        fk = next(iter(UserRole.__table__.columns["user_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"
        assert fk.target_fullname == "auth.users.id"

    def test_role_id_fk_cascade(self) -> None:
        fk = next(iter(UserRole.__table__.columns["role_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"
        assert fk.target_fullname == "auth.roles.id"

    def test_relationships(self) -> None:
        rel_keys = {r.key for r in sa_inspect(UserRole).relationships}
        assert {"user", "role"}.issubset(rel_keys)


# ---------------------------------------------------------------------------
# RolePermission (association)
# ---------------------------------------------------------------------------


class TestRolePermissionModel:
    def test_tablename(self) -> None:
        assert RolePermission.__tablename__ == "role_permissions"

    def test_columns(self) -> None:
        assert _col_names(RolePermission) == {"role_id", "permission_id", "assigned_at"}

    def test_composite_pk(self) -> None:
        pk_cols = {c.name for c in RolePermission.__table__.primary_key.columns}
        assert pk_cols == {"role_id", "permission_id"}

    def test_role_id_fk_cascade(self) -> None:
        fk = next(iter(RolePermission.__table__.columns["role_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"
        assert fk.target_fullname == "auth.roles.id"

    def test_permission_id_fk_cascade(self) -> None:
        fk = next(iter(RolePermission.__table__.columns["permission_id"].foreign_keys))
        assert fk.ondelete == "CASCADE"
        assert fk.target_fullname == "auth.permissions.id"

    def test_relationships(self) -> None:
        rel_keys = {r.key for r in sa_inspect(RolePermission).relationships}
        assert {"role", "permission"}.issubset(rel_keys)
