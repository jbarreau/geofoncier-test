#!/usr/bin/env python3
"""
Mock data script — inserts fake users and tasks so the app has something to display.

All fake accounts share the password: password123

Usage (one-shot after the stack is up):
    docker compose --profile mock run --rm mock-data

Or directly against a running Postgres:
    DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost/geofoncier \
        python scripts/mock_data.py
"""

import asyncio
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import bcrypt

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

MOCK_PASSWORD = "password123"
MOCK_USER_COUNT = 20
MOCK_TASK_COUNT = 40

FIRST_NAMES = [
    "Alice", "Baptiste", "Camille", "David", "Emma", "François", "Gabriel",
    "Hélène", "Inès", "Julien", "Karine", "Laurent", "Marie", "Nicolas",
    "Olivia", "Pierre", "Quentin", "Romain", "Sophie", "Thomas",
    "Ulysse", "Valérie", "William", "Xavier", "Yasmine", "Zoé",
]

LAST_NAMES = [
    "Dupont", "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard",
    "Petit", "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre",
    "Michel", "Garcia", "David", "Bertrand", "Roux", "Vincent",
]

MOCK_TASK_TITLES = [
    "Vérifier les limites de parcelle",
    "Mettre à jour le plan cadastral",
    "Analyser le dossier foncier",
    "Préparer le rapport d'expertise",
    "Contrôler les données GPS",
    "Traiter les demandes de bornage",
    "Réviser le document d'arpentage",
    "Valider les coordonnées géographiques",
    "Numériser les plans anciens",
    "Corriger les erreurs de délimitation",
    "Effectuer le relevé topographique",
    "Rédiger le procès-verbal de bornage",
    "Mettre à jour la base foncière",
    "Instruire le dossier de division parcellaire",
    "Vérifier la conformité des actes notariés",
    "Préparer les pièces pour le géomètre",
    "Analyser les servitudes de passage",
    "Classer les archives cadastrales",
    "Contacter le propriétaire pour rendez-vous",
    "Vérifier l'état des bornes terrain",
    "Établir le tableau des surfaces",
    "Mettre à jour les références cadastrales",
    "Préparer la note de synthèse foncière",
    "Valider le levé planimétrique",
    "Instruire la demande de mutation",
    "Corriger le numéro de parcelle",
    "Finaliser le dossier de fusion",
    "Remettre le rapport au client",
    "Vérifier les emprises sur voirie",
    "Compléter les données attributaires",
]

TASK_STATUSES = ["todo", "doing", "done"]
STATUS_WEIGHTS = [0.4, 0.35, 0.25]  # weighted distribution


async def mock() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Fetch existing roles
        rows = await conn.fetch("SELECT id, name FROM auth.roles")
        if not rows:
            print("[mock] No roles found — run the seed script first.")
            return

        role_map: dict[str, uuid.UUID] = {r["name"]: r["id"] for r in rows}
        assignable_roles = [r for r in role_map if r != "admin"]

        hashed = bcrypt.hashpw(MOCK_PASSWORD.encode(), bcrypt.gensalt()).decode()

        # --- users ---
        created_user_ids: list[uuid.UUID] = []
        created = 0
        for i in range(MOCK_USER_COUNT):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}{i}@mock.geofoncier.local"
            role_name = random.choice(assignable_roles)
            user_id = uuid.uuid4()

            row = await conn.fetchrow(
                """
                INSERT INTO auth.users (id, email, hashed_password)
                VALUES ($1, $2, $3)
                ON CONFLICT (email) DO NOTHING
                RETURNING id
                """,
                user_id,
                email,
                hashed,
            )

            if row:
                await conn.execute(
                    """
                    INSERT INTO auth.user_roles (user_id, role_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    row["id"],
                    role_map[role_name],
                )
                created_user_ids.append(row["id"])
                created += 1

        print(f"[mock] {created} fake user(s) inserted (password: {MOCK_PASSWORD}).")

        # --- tasks ---
        # Fetch all user IDs (seed + mock) to distribute task ownership
        all_users = await conn.fetch("SELECT id FROM auth.users")
        if not all_users:
            print("[mock] No users found, skipping task creation.")
            return

        all_user_ids = [r["id"] for r in all_users]

        existing_tasks = await conn.fetchval("SELECT COUNT(*) FROM tasks.tasks")
        if existing_tasks >= MOCK_TASK_COUNT:
            print(f"[mock] {existing_tasks} tasks already exist, skipping task creation.")
        else:
            now = datetime.now(timezone.utc)
            tasks_created = 0
            for _ in range(MOCK_TASK_COUNT):
                title = random.choice(MOCK_TASK_TITLES)
                description = None
                if random.random() < 0.6:
                    description = f"Dossier n°{random.randint(1000, 9999)} — à traiter en priorité." if random.random() < 0.3 else None
                status = random.choices(TASK_STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
                owner_id = random.choice(all_user_ids)
                # due_date: some overdue (past), some future, some None
                due_date = None
                if random.random() < 0.75:
                    offset_days = random.randint(-15, 45)
                    due_date = now + timedelta(days=offset_days)
                # created_at: spread over the last 60 days
                created_at = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
                # updated_at: between created_at and now (tasks done/doing tend to be updated more recently)
                max_update_offset = int((now - created_at).total_seconds())
                update_offset = random.randint(0, max_update_offset)
                updated_at = created_at + timedelta(seconds=update_offset)

                await conn.execute(
                    """
                    INSERT INTO tasks.tasks (id, title, description, status, owner_id, due_date, created_at, updated_at)
                    VALUES ($1, $2, $3, $4::tasks.taskstatus, $5, $6, $7, $8)
                    """,
                    uuid.uuid4(),
                    title,
                    description,
                    status,
                    owner_id,
                    due_date,
                    created_at,
                    updated_at,
                )
                tasks_created += 1

            print(f"[mock] {tasks_created} fake task(s) inserted.")

        print("[mock] Done.")
    finally:
        await conn.close()


asyncio.run(mock())
