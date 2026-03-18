import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models import Permission
from app.schemas import (
    CreatePermissionRequest,
    PermissionResponse,
    UpdatePermissionRequest,
)
from app.services.permission_service import (
    create_permission,
    delete_permission,
    get_permission,
    list_permissions,
    update_permission,
)

router = APIRouter(prefix="/permissions", tags=["permissions"])

_MANAGE = Depends(require_permission("users:manage"))


@router.get("", response_model=list[PermissionResponse])
async def list_permissions_route(
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> list[Permission]:
    return await list_permissions(db)


@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission_route(
    body: CreatePermissionRequest,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> Permission:
    return await create_permission(db, body.name, body.description)


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission_route(
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> Permission:
    return await get_permission(db, permission_id)


@router.put("/{permission_id}", response_model=PermissionResponse)
async def update_permission_route(
    permission_id: uuid.UUID,
    body: UpdatePermissionRequest,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> Permission:
    return await update_permission(db, permission_id, body.name, body.description)


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission_route(
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> None:
    await delete_permission(db, permission_id)
