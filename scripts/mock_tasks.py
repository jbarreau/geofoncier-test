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
    "Vérifier les bornes cadastrales",
    "Mettre à jour le plan de bornage",
    "Préparer le dossier de division parcellaire",
    "Réaliser le levé topographique",
    "Contrôler les coordonnées GPS",
    "Rédiger le procès-verbal de bornage",
    "Archiver les documents fonciers",
    "Contacter le service de publicité foncière",
    "Mettre à jour les données SIG",
    "Vérifier la conformité du titre de propriété",
    "Analyser le plan de remembrement",
    "Préparer la réunion de bornage",
    "Traiter les réclamations riveraines",
    "Effectuer le relevé des servitudes",
    "Valider les coordonnées Lambert",
    "Corriger les erreurs de cadastre",
    "Numériser les plans anciens",
    "Calculer les surfaces de parcelles",
    "Rédiger le rapport d'expertise foncière",
    "Contrôler l'implantation des bornes",
]

TASK_DESCRIPTIONS = [
    "Intervention sur le terrain requise.",
    "Document à transmettre au client sous 5 jours.",
    "Vérification croisée avec les données de la mairie.",
    None,
    "Urgence signalée par le client.",
    None,
    "Coordination avec le géomètre-expert associé.",
    None,
    "Données à intégrer dans le système SIG communal.",
    "Validation nécessaire avant dépôt au service foncier.",
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
