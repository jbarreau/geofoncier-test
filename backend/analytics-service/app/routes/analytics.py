from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import PERM_ANALYTICS_ADMIN, PERM_ANALYTICS_READ, TASK_STATUS_DONE
from app.database import get_db
from app.models.task import Task
from app.schemas.analytics import (
    ByUserResponse,
    OverTimeResponse,
    OverdueResponse,
    OverdueTask,
    StatusCount,
    SummaryResponse,
    TimePoint,
    UserTaskCount,
)
from geofoncier_shared.fastapi.middleware.jwt import require_permission
from geofoncier_shared.fastapi.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    _: CurrentUser = require_permission(PERM_ANALYTICS_READ),
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
    _: CurrentUser = require_permission(PERM_ANALYTICS_READ),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=500, ge=1, le=1000),
) -> OverdueResponse:
    now = datetime.now(timezone.utc)
    rows = await db.execute(
        select(Task.id, Task.title, Task.status, Task.owner_id, Task.due_date)
        .where(Task.due_date < now, Task.status != TASK_STATUS_DONE)
        .limit(limit)
    )
    tasks = rows.all()
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
    _: CurrentUser = require_permission(PERM_ANALYTICS_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> ByUserResponse:
    rows = await db.execute(
        select(Task.owner_id, func.count().label("count")).group_by(Task.owner_id)
    )
    return ByUserResponse(
        by_user=[UserTaskCount(owner_id=row.owner_id, count=row.count) for row in rows]
    )


@router.get("/over-time", response_model=OverTimeResponse)
async def get_over_time(
    _: CurrentUser = require_permission(PERM_ANALYTICS_READ),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=7, le=90),
) -> OverTimeResponse:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await db.execute(
        select(
            cast(Task.created_at, Date).label("date"),
            func.count().label("count"),
        )
        .where(Task.created_at >= since)
        .group_by(cast(Task.created_at, Date))
        .order_by(cast(Task.created_at, Date))
    )
    return OverTimeResponse(
        points=[TimePoint(date=str(row.date), count=row.count) for row in rows]
    )
