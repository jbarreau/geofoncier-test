"""create tasks schema tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS tasks")

    op.execute("CREATE TYPE tasks.taskstatus AS ENUM ('todo', 'doing', 'done')")

    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("todo", "doing", "done", name="taskstatus", schema="tasks"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="tasks",
    )
    op.create_index(
        op.f("ix_tasks_tasks_owner_id"),
        "tasks",
        ["owner_id"],
        unique=False,
        schema="tasks",
    )

    op.create_table(
        "task_assignments",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "user_id"),
        schema="tasks",
    )

    op.create_table(
        "task_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("todo", "doing", "done", name="taskstatus", schema="tasks"),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="tasks",
    )
    op.create_index(
        op.f("ix_tasks_task_status_history_task_id"),
        "task_status_history",
        ["task_id"],
        unique=False,
        schema="tasks",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tasks_task_status_history_task_id"),
        table_name="task_status_history",
        schema="tasks",
    )
    op.drop_table("task_status_history", schema="tasks")
    op.drop_table("task_assignments", schema="tasks")
    op.drop_index(op.f("ix_tasks_tasks_owner_id"), table_name="tasks", schema="tasks")
    op.drop_table("tasks", schema="tasks")
    op.execute("DROP TYPE IF EXISTS tasks.taskstatus")
