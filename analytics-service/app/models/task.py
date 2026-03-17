import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, func
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Task(Base):
    """Read-only mapping of tasks.tasks — analytics-service never writes."""

    __tablename__ = "tasks"
    __table_args__ = {"schema": "tasks"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        PgEnum("todo", "doing", "done", name="taskstatus", schema="tasks", create_type=False)
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
