import uuid
from datetime import datetime

from pydantic import BaseModel


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


class TimePoint(BaseModel):
    date: str  # ISO date "YYYY-MM-DD"
    count: int


class OverTimeResponse(BaseModel):
    points: list[TimePoint]
