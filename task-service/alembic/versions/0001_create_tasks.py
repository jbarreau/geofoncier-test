"""create tasks and task_status_history tables

Revision ID: 0001
Revises:
Create Date: 2026-03-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE taskstatus AS ENUM ('pending', 'in_progress', 'done', 'cancelled')")

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "in_progress", "done", "cancelled", name="taskstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "task_status_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Uuid(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "old_status",
            sa.Enum("pending", "in_progress", "done", "cancelled", name="taskstatus"),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            sa.Enum("pending", "in_progress", "done", "cancelled", name="taskstatus"),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("changed_by", sa.Uuid(), nullable=False),
    )

    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"])
    op.create_index("ix_task_status_history_task_id", "task_status_history", ["task_id"])


def downgrade() -> None:
    op.drop_table("task_status_history")
    op.drop_table("tasks")
    op.execute("DROP TYPE taskstatus")
