import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services import task_service
from geofoncier_shared.fastapi.middleware.jwt import require_permission
from geofoncier_shared.fastapi.schemas.auth import CurrentUser

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", status_code=201, response_model=TaskResponse)
async def create_task(
    body: TaskCreate,
    current_user: CurrentUser = require_permission("task:create"),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await task_service.create_task(db, body, current_user.user_id)
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: CurrentUser = require_permission("task:read"),
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    owner_filter = current_user.user_id if "viewer" in current_user.roles else None
    tasks = await task_service.list_tasks(db, owner_id=owner_filter)
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    current_user: CurrentUser = require_permission("task:read"),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if "viewer" in current_user.roles and task.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: CurrentUser = require_permission("task:update"),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task = await task_service.update_task(db, task, body)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    current_user: CurrentUser = require_permission("task:delete"),
    db: AsyncSession = Depends(get_db),
) -> None:
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin role required")

    task = await task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await task_service.delete_task(db, task)
