import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import PermissionNameConflictError, PermissionNotFoundError
from ..models import Permission


async def list_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission).order_by(Permission.name))
    return list(result.scalars().all())


async def get_permission(db: AsyncSession, permission_id: uuid.UUID) -> Permission:
    result = await db.execute(select(Permission).where(Permission.id == permission_id))
    perm = result.scalar_one_or_none()
    if perm is None:
        raise PermissionNotFoundError()
    return perm


async def create_permission(
    db: AsyncSession, name: str, description: str | None
) -> Permission:
    perm = Permission(name=name, description=description)
    db.add(perm)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise PermissionNameConflictError()
    await db.refresh(perm)
    return perm


async def update_permission(
    db: AsyncSession,
    permission_id: uuid.UUID,
    name: str | None,
    description: str | None,
) -> Permission:
    perm = await get_permission(db, permission_id)
    if name is not None:
        perm.name = name
    if description is not None:
        perm.description = description
    db.add(perm)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise PermissionNameConflictError()
    await db.refresh(perm)
    return perm


async def delete_permission(db: AsyncSession, permission_id: uuid.UUID) -> None:
    perm = await get_permission(db, permission_id)
    await db.delete(perm)
    await db.commit()
