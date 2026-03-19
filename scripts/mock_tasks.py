#!/usr/bin/env python3
"""
Mock tasks script — inserts ~50 fake tasks into postgres-tasks.

Reads all user IDs from postgres-auth (AUTH_DATABASE_URL) so tasks are
assigned to real users.  Writes to postgres-tasks (DATABASE_URL).

Usage (one-shot after the stack is up):
    docker compose --profile mock run --rm mock-tasks

Or directly against running Postgres instances:
    AUTH_DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost:5432/geofoncier_auth \\
    DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost:5433/geofoncier_tasks \\
        python scripts/mock_tasks.py
"""

import asyncio
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg

AUTH_DATABASE_URL = os.environ["AUTH_DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

MOCK_TASK_COUNT = 50

TASK_TITLES = [
    "Verify cadastral boundary markers",
    "Update boundary survey plan",
    "Prepare plot subdivision file",
    "Carry out topographic survey",
    "Check GPS coordinates",
    "Draft boundary demarcation report",
    "Archive land registry documents",
    "Contact the land publicity service",
    "Update GIS data",
    "Verify property title compliance",
    "Analyse land consolidation plan",
    "Prepare boundary demarcation meeting",
    "Process neighbour complaints",
    "Carry out easement survey",
    "Validate Lambert coordinates",
    "Correct cadastral errors",
    "Digitise old plans",
    "Calculate parcel areas",
    "Write land expertise report",
    "Check boundary marker installation",
]

TASK_DESCRIPTIONS = [
    "Field intervention required.",
    "Document to be sent to client within 5 days.",
    "Cross-check with town hall data.",
    None,
    "Urgent — flagged by client.",
    None,
    "Coordination with associated licensed surveyor.",
    None,
    "Data to be integrated into the municipal GIS system.",
    "Validation required before submission to land registry office.",
]

STATUSES = ["todo", "doing", "done"]
STATUS_WEIGHTS = [0.5, 0.3, 0.2]


def random_due_date(now: datetime) -> datetime | None:
    """Return a random due date (past or future) or None."""
    if random.random() < 0.2:
        return None
    offset_days = random.randint(-30, 60)
    return now + timedelta(days=offset_days)


async def mock() -> None:
    auth_conn = await asyncpg.connect(AUTH_DATABASE_URL)
    tasks_conn = await asyncpg.connect(DATABASE_URL)
    try:
        user_rows = await auth_conn.fetch("SELECT id FROM auth.users")
        if not user_rows:
            print("[mock-tasks] No users found — run mock-users (or seed) first.")
            return

        user_ids = [r["id"] for r in user_rows]
        print(f"[mock-tasks] Found {len(user_ids)} user(s) to assign tasks to.")

        now = datetime.now(timezone.utc)
        created = 0
        for _ in range(MOCK_TASK_COUNT):
            task_id = uuid.uuid4()
            title = random.choice(TASK_TITLES)
            description = random.choice(TASK_DESCRIPTIONS)
            status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
            owner_id = random.choice(user_ids)
            due_date = random_due_date(now)
            # Spread created_at over the last 60 days for realistic analytics
            created_at = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
            # updated_at: always >= created_at, <= now
            max_offset = int((now - created_at).total_seconds())
            updated_at = created_at + timedelta(seconds=random.randint(0, max_offset))

            row = await tasks_conn.fetchrow(
                """
                INSERT INTO tasks.tasks (id, title, description, status, owner_id, due_date, created_at, updated_at)
                VALUES ($1, $2, $3, $4::tasks.taskstatus, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
                RETURNING id
                """,
                task_id,
                title,
                description,
                status,
                owner_id,
                due_date,
                created_at,
                updated_at,
            )

            if row:
                created += 1

        print(f"[mock-tasks] {created} fake task(s) inserted.")
        print("[mock-tasks] Done.")
    finally:
        await auth_conn.close()
        await tasks_conn.close()


asyncio.run(mock())
