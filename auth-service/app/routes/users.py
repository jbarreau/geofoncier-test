import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.schemas import UpdateUserRequest, UserDetailResponse
from app.services.user_service import (
    assign_role_to_user,
    get_user,
    list_users,
    remove_role_from_user,
    update_user,
)

router = APIRouter(prefix="/api/users", tags=["users"])

_MANAGE = Depends(require_permission("users:manage"))


@router.get("", response_model=list[UserDetailResponse])
async def list_users_route(
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> list:
    return await list_users(db)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user_route(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await get_user(db, user_id)


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user_route(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await update_user(db, user_id, body.is_active)


@router.post(
    "/{user_id}/roles/{role_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def assign_role_route(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await assign_role_to_user(db, user_id, role_id)


@router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_role_route(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: list[str] = _MANAGE,
) -> object:
    return await remove_role_from_user(db, user_id, role_id)
