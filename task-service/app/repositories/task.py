import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task, TaskStatus, TaskStatusHistory


async def create_task(
    db: AsyncSession,
    title: str,
    description: str | None,
    owner_id: uuid.UUID,
    created_by: uuid.UUID,
) -> Task:
    task = Task(title=title, description=description, owner_id=owner_id)
    db.add(task)
    await db.flush()

    history = TaskStatusHistory(
        task_id=task.id,
        old_status=None,
        new_status=task.status,
        changed_by=created_by,
    )
    db.add(history)
    await db.commit()
    await db.refresh(task)
    return task


async def get_tasks(
    db: AsyncSession,
    owner_id: uuid.UUID | None = None,
) -> list[Task]:
    stmt = select(Task)
    if owner_id is not None:
        stmt = stmt.where(Task.owner_id == owner_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def update_task(
    db: AsyncSession,
    task: Task,
    title: str | None,
    description: str | None,
    status: TaskStatus | None,
    changed_by: uuid.UUID,
) -> Task:
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description

    if status is not None and status != task.status:
        history = TaskStatusHistory(
            task_id=task.id,
            old_status=task.status,
            new_status=status,
            changed_by=changed_by,
        )
        db.add(history)
        task.status = status

    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.commit()
