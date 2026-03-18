import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import (
    PermissionNotFoundError,
    RoleNameConflictError,
    RoleNotFoundError,
    RolePermissionAlreadyAssignedError,
    RolePermissionNotFoundError,
)
from app.models import Permission, Role, RolePermission


async def _load_role_with_permissions(db: AsyncSession, role_id: uuid.UUID) -> Role:
    result = await db.execute(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise RoleNotFoundError()
    return role


async def list_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(
        select(Role)
        .order_by(Role.name)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
    )
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: uuid.UUID) -> Role:
    return await _load_role_with_permissions(db, role_id)


async def create_role(db: AsyncSession, name: str, description: str | None) -> Role:
    role = Role(name=name, description=description)
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise RoleNameConflictError()
    await db.refresh(role)
    return await _load_role_with_permissions(db, role.id)


async def update_role(
    db: AsyncSession,
    role_id: uuid.UUID,
    name: str | None,
    description: str | None,
) -> Role:
    role = await _load_role_with_permissions(db, role_id)
    if name is not None:
        role.name = name
    if description is not None:
        role.description = description
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise RoleNameConflictError()
    await db.refresh(role)
    return await _load_role_with_permissions(db, role.id)


async def delete_role(db: AsyncSession, role_id: uuid.UUID) -> None:
    role = await _load_role_with_permissions(db, role_id)
    await db.delete(role)
    await db.commit()


async def assign_permission_to_role(
    db: AsyncSession,
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
) -> Role:
    # Verify role and permission exist
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    if role_result.scalar_one_or_none() is None:
        raise RoleNotFoundError()

    perm_result = await db.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    if perm_result.scalar_one_or_none() is None:
        raise PermissionNotFoundError()

    # Check if already assigned
    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise RolePermissionAlreadyAssignedError()

    db.add(RolePermission(role_id=role_id, permission_id=permission_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise RolePermissionAlreadyAssignedError()

    return await _load_role_with_permissions(db, role_id)


async def remove_permission_from_role(
    db: AsyncSession,
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
) -> Role:
    # Verify role exists
    role_result = await db.execute(select(Role).where(Role.id == role_id))
    if role_result.scalar_one_or_none() is None:
        raise RoleNotFoundError()

    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    role_perm = result.scalar_one_or_none()
    if role_perm is None:
        raise RolePermissionNotFoundError()

    await db.delete(role_perm)
    await db.commit()

    return await _load_role_with_permissions(db, role_id)
