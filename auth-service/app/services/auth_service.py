import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from asyncpg import UniqueViolationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from ..models import Permission, RefreshToken, Role, RolePermission, User, UserRole
from ..schemas import TokenResponse, UserResponse
from .password_service import hash_password, verify_password
from .token_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    verify_refresh_token,
)

_DEFAULT_ROLE = "viewer"
_TIMING_DUMMY_HASH = "$2b$12$invalidhashfortimingreasononly00000"


async def _load_roles_and_permissions(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[list[str], list[str]]:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.roles)
            .selectinload(UserRole.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
    )
    user = result.scalar_one()

    role_names = [ur.role.name for ur in user.roles]
    permission_names = list(
        {rp.permission.name for ur in user.roles for rp in ur.role.permissions}
    )
    return role_names, permission_names


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> UserResponse:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise EmailAlreadyExistsError()

    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.flush()

    role_result = await db.execute(select(Role).where(Role.name == _DEFAULT_ROLE))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise RuntimeError(
            f"Default role '{_DEFAULT_ROLE}' not found. Run the seed script first."
        )

    db.add(UserRole(user_id=user.id, role_id=role.id))

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if exc.orig and isinstance(exc.orig.__cause__, UniqueViolationError):
            raise EmailAlreadyExistsError() from exc
        raise

    await db.refresh(user)
    return UserResponse.model_validate(user)


async def login_user(
    db: AsyncSession,
    redis: aioredis.Redis,
    email: str,
    password: str,
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Always run bcrypt to prevent timing-based user enumeration
    hashed = user.hashed_password if user is not None else _TIMING_DUMMY_HASH
    if not verify_password(password, hashed) or user is None:
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveUserError()

    role_names, permission_names = await _load_roles_and_permissions(db, user.id)

    access_token, _jti, _exp = create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
        permissions=permission_names,
    )
    raw_refresh, token_hash, refresh_expires_at, db_id = create_refresh_token()

    db.add(
        RefreshToken(
            id=db_id,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=refresh_expires_at,
        )
    )
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


async def refresh_tokens(
    db: AsyncSession,
    redis: aioredis.Redis,
    raw_refresh_token: str,
) -> TokenResponse:
    # Parse the db_id embedded in the raw token for O(1) lookup
    try:
        db_id_str, _ = raw_refresh_token.split(":", 1)
        db_id = uuid.UUID(db_id_str)
    except (ValueError, AttributeError):
        raise InvalidRefreshTokenError()

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == db_id,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > now,
        )
    )
    token_record = result.scalar_one_or_none()

    if token_record is None or not verify_refresh_token(
        raw_refresh_token, token_record.token_hash
    ):
        raise InvalidRefreshTokenError()

    user_result = await db.execute(select(User).where(User.id == token_record.user_id))
    user = user_result.scalar_one()

    if not user.is_active:
        raise InactiveUserError()

    role_names, permission_names = await _load_roles_and_permissions(db, user.id)

    # Revoke old token
    token_record.revoked = True
    db.add(token_record)

    # Issue new token pair
    access_token, _jti, _exp = create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
        permissions=permission_names,
    )
    raw_refresh, token_hash, refresh_expires_at, new_db_id = create_refresh_token()

    db.add(
        RefreshToken(
            id=new_db_id,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=refresh_expires_at,
        )
    )
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


async def logout_user(
    db: AsyncSession,
    redis: aioredis.Redis,
    access_token: str,
    raw_refresh_token: str,
) -> None:
    # Blacklist the access token JTI in Redis with remaining TTL
    try:
        payload = decode_access_token(access_token)
        jti = payload["jti"]
        exp = (
            int(payload["exp"].timestamp())
            if hasattr(payload["exp"], "timestamp")
            else int(payload["exp"])
        )
        now_ts = int(datetime.now(timezone.utc).timestamp())
        ttl = max(exp - now_ts, 1)
        await redis.setex(f"blacklist:{jti}", ttl, "1")
    except Exception:
        # Token already expired or invalid — nothing to blacklist, still revoke refresh
        pass

    # Revoke the refresh token
    try:
        db_id_str, _ = raw_refresh_token.split(":", 1)
        db_id = uuid.UUID(db_id_str)
    except (ValueError, AttributeError):
        return

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == db_id,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > now,
        )
    )
    token_record = result.scalar_one_or_none()

    if token_record and verify_refresh_token(
        raw_refresh_token, token_record.token_hash
    ):
        token_record.revoked = True
        db.add(token_record)
        await db.commit()
