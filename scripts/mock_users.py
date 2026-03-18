#!/usr/bin/env python3
"""
Mock users script — inserts ~20 fake users into postgres-auth.

All fake accounts share the password: password123

Usage (one-shot after the stack is up):
    docker compose --profile mock run --rm mock-users

Or directly against a running Postgres:
    DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost/geofoncier_auth \
        python scripts/mock_users.py
"""

import asyncio
import os
import random
import uuid

import asyncpg
import bcrypt

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

MOCK_PASSWORD = "password123"
MOCK_USER_COUNT = 20

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


async def mock() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("SELECT id, name FROM auth.roles")
        if not rows:
            print("[mock] No roles found — run the seed script first.")
            return

        role_map: dict[str, uuid.UUID] = {r["name"]: r["id"] for r in rows}
        assignable_roles = [r for r in role_map if r != "admin"]

        hashed = bcrypt.hashpw(MOCK_PASSWORD.encode(), bcrypt.gensalt()).decode()

        created = 0
        for i in range(MOCK_USER_COUNT):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}{i}@mock.geofoncier.local"
            role_name = random.choice(assignable_roles)

            row = await conn.fetchrow(
                """
                INSERT INTO auth.users (id, email, hashed_password)
                VALUES ($1, $2, $3)
                ON CONFLICT (email) DO NOTHING
                RETURNING id
                """,
                uuid.uuid4(),
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
                created += 1

        print(f"[mock] {created} fake user(s) inserted (password: {MOCK_PASSWORD}).")
        print("[mock] Done.")
    finally:
        await conn.close()


asyncio.run(mock())
