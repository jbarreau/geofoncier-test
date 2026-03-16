import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task, TaskStatus
from ..repositories import task as repo
from ..schemas.task import TaskCreate, TaskUpdate


async def create_task(db: AsyncSession, payload: TaskCreate, owner_id: uuid.UUID) -> Task:
    return await repo.create_task(
        db,
        title=payload.title,
        description=payload.description,
        owner_id=owner_id,
        created_by=owner_id,
    )


async def list_tasks(
    db: AsyncSession,
    owner_filter: uuid.UUID | None = None,
) -> list[Task]:
    return await repo.get_tasks(db, owner_id=owner_filter)


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task:
    task = await repo.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def update_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    changed_by: uuid.UUID,
) -> Task:
    task = await repo.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return await repo.update_task(
        db,
        task=task,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        changed_by=changed_by,
    )


async def delete_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    current_roles: list[str],
) -> None:
    if "admin" not in current_roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    task = await repo.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await repo.delete_task(db, task)
