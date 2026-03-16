import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.jwt import require_permission
from ..schemas.auth import CurrentUser
from ..schemas.task import TaskCreate, TaskRead, TaskUpdate
from ..services import task as svc

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = require_permission("task:create"),
) -> TaskRead:
    task = await svc.create_task(db, payload, owner_id=current_user.user_id)
    return TaskRead.model_validate(task)


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = require_permission("task:read"),
) -> list[TaskRead]:
    owner_filter: uuid.UUID | None = None
    if "viewer" in current_user.roles and "admin" not in current_user.roles:
        owner_filter = current_user.user_id
    tasks = await svc.list_tasks(db, owner_filter=owner_filter)
    return [TaskRead.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = require_permission("task:read"),
) -> TaskRead:
    task = await svc.get_task(db, task_id)
    return TaskRead.model_validate(task)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = require_permission("task:update"),
) -> TaskRead:
    task = await svc.update_task(db, task_id, payload, changed_by=current_user.user_id)
    return TaskRead.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = require_permission("task:delete"),
) -> None:
    await svc.delete_task(db, task_id, current_roles=current_user.roles)
