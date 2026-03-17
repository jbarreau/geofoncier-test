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

    # CREATE TYPE IF NOT EXISTS is not supported in PostgreSQL; use a DO block.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tasks.taskstatus AS ENUM ('todo', 'doing', 'done');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks.tasks (
            id          UUID                  NOT NULL,
            title       VARCHAR(255)          NOT NULL,
            description TEXT,
            status      tasks.taskstatus      NOT NULL,
            owner_id    UUID                  NOT NULL,
            due_date    TIMESTAMPTZ,
            created_at  TIMESTAMPTZ           NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ           NOT NULL DEFAULT now(),
            PRIMARY KEY (id)
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tasks_tasks_owner_id
        ON tasks.tasks (owner_id)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks.task_assignments (
            task_id UUID NOT NULL,
            user_id UUID NOT NULL,
            PRIMARY KEY (task_id, user_id),
            FOREIGN KEY (task_id) REFERENCES tasks.tasks (id) ON DELETE CASCADE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks.task_status_history (
            id         UUID             NOT NULL,
            task_id    UUID             NOT NULL,
            status     tasks.taskstatus NOT NULL,
            changed_at TIMESTAMPTZ      NOT NULL DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY (task_id) REFERENCES tasks.tasks (id) ON DELETE CASCADE
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tasks_task_status_history_task_id
        ON tasks.task_status_history (task_id)
    """)


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
