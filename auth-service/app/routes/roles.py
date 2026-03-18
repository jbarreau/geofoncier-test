import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.schemas import CreateRoleRequest, RoleResponse, UpdateRoleRequest
from app.services.role_service import (
    assign_permission_to_role,
    create_role,
    delete_role,
    get_role,
    list_roles,
    remove_permission_from_role,
    update_role,
)

router = APIRouter(prefix="/roles", tags=["roles"])

_MANAGE = Depends(require_permission("users:manage"))


@router.get("", response_model=list[RoleResponse])
async def list_roles_route(
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> list:
    return await list_roles(db)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role_route(
    body: CreateRoleRequest,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await create_role(db, body.name, body.description)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_route(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await get_role(db, role_id)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role_route(
    role_id: uuid.UUID,
    body: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await update_role(db, role_id, body.name, body.description)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_route(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> None:
    await delete_role(db, role_id)


@router.post(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
)
async def assign_permission_route(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await assign_permission_to_role(db, role_id, permission_id)


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_permission_route(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await remove_permission_from_role(db, role_id, permission_id)
