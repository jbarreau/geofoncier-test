import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..exceptions import (
    RoleNotFoundError,
    UserNotFoundError,
    UserRoleAlreadyAssignedError,
    UserRoleNotFoundError,
)
from ..models import Role, RolePermission, User, UserRole


async def _load_user_with_roles(db: AsyncSession, user_id: uuid.UUID) -> User:
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
    user = result.scalar_one_or_none()
    if user is None:
        raise UserNotFoundError()
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User)
        .order_by(User.email)
        .options(
            selectinload(User.roles)
            .selectinload(UserRole.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
    )
    return list(result.scalars().all())


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    return await _load_user_with_roles(db, user_id)


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    is_active: bool | None,
) -> User:
    user = await _load_user_with_roles(db, user_id)
    if is_active is not None:
        user.is_active = is_active
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _load_user_with_roles(db, user_id)


async def assign_role_to_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
) -> User:
    # Verify user and role exist
    user_result = await db.execute(select(User).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise UserNotFoundError()

    role_result = await db.execute(select(Role).where(Role.id == role_id))
    if role_result.scalar_one_or_none() is None:
        raise RoleNotFoundError()

    # Check if already assigned
    existing = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise UserRoleAlreadyAssignedError()

    db.add(UserRole(user_id=user_id, role_id=role_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise UserRoleAlreadyAssignedError()

    return await _load_user_with_roles(db, user_id)


async def remove_role_from_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
) -> User:
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise UserNotFoundError()

    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    user_role = result.scalar_one_or_none()
    if user_role is None:
        raise UserRoleNotFoundError()

    await db.delete(user_role)
    await db.commit()

    return await _load_user_with_roles(db, user_id)
