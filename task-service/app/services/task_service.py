import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task, TaskStatusHistory
from ..schemas.task import TaskCreate, TaskUpdate


async def create_task(db: AsyncSession, data: TaskCreate, owner_id: uuid.UUID) -> Task:
    task = Task(
        title=data.title,
        description=data.description,
        status=data.status,
        owner_id=owner_id,
        due_date=data.due_date,
    )
    db.add(task)
    await db.flush()

    history = TaskStatusHistory(task_id=task.id, status=task.status)
    db.add(history)

    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(db: AsyncSession, owner_id: uuid.UUID | None = None) -> list[Task]:
    stmt = select(Task)
    if owner_id is not None:
        stmt = stmt.where(Task.owner_id == owner_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def update_task(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
    old_status = task.status

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.status is not None:
        task.status = data.status
    if data.due_date is not None:
        task.due_date = data.due_date

    task.updated_at = datetime.now(timezone.utc)

    if data.status is not None and data.status != old_status:
        history = TaskStatusHistory(task_id=task.id, status=data.status)
        db.add(history)

    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.commit()
