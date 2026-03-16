import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from ..models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    owner_id: uuid.UUID
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TaskStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    status: TaskStatus
    changed_at: datetime
