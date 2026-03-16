import uuid
from datetime import datetime

from pydantic import BaseModel

from ..models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None


class TaskStatusHistoryRead(BaseModel):
    id: uuid.UUID
    old_status: TaskStatus | None
    new_status: TaskStatus
    changed_at: datetime
    changed_by: uuid.UUID

    model_config = {"from_attributes": True}


class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
