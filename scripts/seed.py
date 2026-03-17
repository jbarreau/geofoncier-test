#!/usr/bin/env python3
"""
Seed script — inserts default roles, permissions, and users.

Idempotent: safe to run multiple times.

Default accounts
----------------
admin@geofoncier.local   password: admin123   role: admin
user@geofoncier.local    password: user123    role: user
viewer@geofoncier.local  password: viewer123  role: viewer
"""

import asyncio
import os
import uuid

import asyncpg
import bcrypt

# asyncpg uses the plain postgresql:// scheme
DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")

PERMISSIONS: list[tuple[str, str]] = [
    ("task:create", "Create tasks"),
    ("task:read", "Read tasks"),
    ("task:update", "Update tasks"),
    ("task:delete", "Delete tasks"),
    ("analytics:read", "Read analytics"),
    ("analytics:admin", "Admin analytics (by-user aggregates)"),
    ("users:manage", "Manage users"),
]

ROLES: dict[str, dict] = {
    "admin": {
        "description": "Full access to all resources",
        "permissions": [
            "task:create",
            "task:read",
            "task:update",
            "task:delete",
            "analytics:read",
            "analytics:admin",
            "users:manage",
        ],
    },
    "user": {
        "description": "Standard user — can manage own tasks",
        "permissions": ["task:create", "task:read", "task:update"],
    },
    "viewer": {
        "description": "Read-only access",
        "permissions": ["task:read", "analytics:read"],
    },
}

USERS: list[dict] = [
    {"email": "admin@geofoncier.local", "password": "admin123", "role": "admin"},
    {"email": "user@geofoncier.local", "password": "user123", "role": "user"},
    {"email": "viewer@geofoncier.local", "password": "viewer123", "role": "viewer"},
]


async def seed() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # --- permissions ---
        permission_ids: dict[str, uuid.UUID] = {}
        for name, description in PERMISSIONS:
            row = await conn.fetchrow(
                """
                INSERT INTO auth.permissions (id, name, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                RETURNING id
                """,
                uuid.uuid4(),
                name,
                description,
            )
            permission_ids[name] = row["id"]
        print(f"[seed] {len(permission_ids)} permissions upserted.")

        # --- roles + role_permissions ---
        role_ids: dict[str, uuid.UUID] = {}
        for role_name, role_data in ROLES.items():
            row = await conn.fetchrow(
                """
                INSERT INTO auth.roles (id, name, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                RETURNING id
                """,
                uuid.uuid4(),
                role_name,
                role_data["description"],
            )
            role_ids[role_name] = row["id"]

            for perm_name in role_data["permissions"]:
                await conn.execute(
                    """
                    INSERT INTO auth.role_permissions (role_id, permission_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    role_ids[role_name],
                    permission_ids[perm_name],
                )
        print(f"[seed] {len(role_ids)} roles upserted.")

        # --- users + user_roles ---
        created = 0
        for user_data in USERS:
            hashed = bcrypt.hashpw(
                user_data["password"].encode(), bcrypt.gensalt()
            ).decode()

            row = await conn.fetchrow(
                """
                INSERT INTO auth.users (id, email, hashed_password)
                VALUES ($1, $2, $3)
                ON CONFLICT (email) DO NOTHING
                RETURNING id
                """,
                uuid.uuid4(),
                user_data["email"],
                hashed,
            )

            if row:
                user_id = row["id"]
                created += 1
            else:
                existing = await conn.fetchrow(
                    "SELECT id FROM auth.users WHERE email = $1", user_data["email"]
                )
                user_id = existing["id"]

            await conn.execute(
                """
                INSERT INTO auth.user_roles (user_id, role_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                user_id,
                role_ids[user_data["role"]],
            )

        print(f"[seed] {created} new user(s) created ({len(USERS) - created} already existed).")
        print("[seed] Done.")
    finally:
        await conn.close()


asyncio.run(seed())
