import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..middleware.jwt import require_permission
from ..models.task import Task
from ..schemas.auth import CurrentUser

router = APIRouter(prefix="/analytics", tags=["analytics"])


class StatusCount(BaseModel):
    status: str
    count: int


class SummaryResponse(BaseModel):
    total: int
    by_status: list[StatusCount]


class OverdueTask(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    owner_id: uuid.UUID
    due_date: datetime


class OverdueResponse(BaseModel):
    count: int
    tasks: list[OverdueTask]


class UserTaskCount(BaseModel):
    owner_id: uuid.UUID
    count: int


class ByUserResponse(BaseModel):
    by_user: list[UserTaskCount]


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    _: CurrentUser = require_permission("analytics:read"),
    db: AsyncSession = Depends(get_db),
) -> SummaryResponse:
    rows = await db.execute(
        select(Task.status, func.count().label("count")).group_by(Task.status)
    )
    by_status = [StatusCount(status=row.status, count=row.count) for row in rows]
    total = sum(s.count for s in by_status)
    return SummaryResponse(total=total, by_status=by_status)


@router.get("/overdue", response_model=OverdueResponse)
async def get_overdue(
    _: CurrentUser = require_permission("analytics:read"),
    db: AsyncSession = Depends(get_db),
) -> OverdueResponse:
    now = datetime.now(timezone.utc)
    rows = await db.execute(
        select(Task).where(Task.due_date < now, Task.status != "done")
    )
    tasks = rows.scalars().all()
    return OverdueResponse(
        count=len(tasks),
        tasks=[
            OverdueTask(
                id=t.id,
                title=t.title,
                status=t.status,
                owner_id=t.owner_id,
                due_date=t.due_date,
            )
            for t in tasks
        ],
    )


@router.get("/by-user", response_model=ByUserResponse)
async def get_by_user(
    _: CurrentUser = require_permission("analytics:admin"),
    db: AsyncSession = Depends(get_db),
) -> ByUserResponse:
    rows = await db.execute(
        select(Task.owner_id, func.count().label("count")).group_by(Task.owner_id)
    )
    return ByUserResponse(
        by_user=[UserTaskCount(owner_id=row.owner_id, count=row.count) for row in rows]
    )
