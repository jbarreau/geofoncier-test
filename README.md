# Géofoncier

Task management application with RBAC, JWT RS256 authentication, and three independent FastAPI microservices.

---

## Option 1 — Docker (recommended)

> Requires Docker Desktop ≥ 4.x

### First launch

```bash
# Builds images, generates RSA keys, runs migrations, seeds the database
docker compose up --build
```

The startup sequence is fully automated:

1. **keygen** — generates an RSA-2048 key pair into a named Docker volume (`jwt_keys`). Skipped on subsequent runs.
2. **migrate** / **migrate-tasks** — runs `alembic upgrade head` for each service. Idempotent.
3. **seed** — inserts default roles, permissions, and users. Idempotent.
4. **services** — auth, task, analytics, and frontend start once the above complete.

### Subsequent runs

```bash
docker compose up
```

### Mock data (optional)

Populate the database with ~20 fake users and ~50 fake tasks for front-end development:

```bash
# Run once after the stack is up
docker compose --profile mock run --rm mock-users
docker compose --profile mock run --rm mock-tasks
```

All mock accounts share the password `password123` and are assigned `user` or `viewer` roles.
Re-running the commands is safe — already-existing records are skipped.

---

## Default accounts

| Email | Password | Role |
|---|---|---|
| admin@geofoncier.local | admin123 | admin |
| user@geofoncier.local | user123 | user |
| viewer@geofoncier.local | viewer123 | viewer |

---

## Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:80 |
| auth-service | http://localhost:8000 |
| task-service | http://localhost:8001 |
| analytics-service | http://localhost:8002 |

---

## Option 2 — Local dev (with venv)

Run the infrastructure in Docker and each service locally for hot-reload and debugger support.

### Prerequisites

- Python 3.12
- Node.js 20+
- Docker Desktop (for PostgreSQL + Redis)

### Step 1 — Start infrastructure only

```bash
docker compose up postgres-auth postgres-tasks redis
```

### Step 2 — Extract JWT keys

On first run, extract the RSA keys from the Docker volume (requires the full stack to have been started at least once):

```bash
mkdir -p keys
docker run --rm \
  -v geofoncier-test_jwt_keys:/keys \
  -v "$(pwd)/keys":/out \
  alpine cp /keys/private.pem /keys/public.pem /out/
```

Or generate a fresh pair locally:

```bash
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

> The `keys/` directory is gitignored.

### Step 3 — Run database migrations

```bash
# auth-service
cd backend/auth-service
DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost:5432/geofoncier_auth \
JWT_PRIVATE_KEY_PATH=../../keys/private.pem \
JWT_PUBLIC_KEY_PATH=../../keys/public.pem \
  alembic upgrade head

# task-service
cd backend/task-service
DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost:5433/geofoncier_tasks \
  alembic upgrade head
```

### Step 4 — Seed default data

```bash
cd backend/auth-service
DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost:5432/geofoncier_auth \
  python ../../scripts/seed.py
```

### Step 5 — Set up and start each service

Each service has its own virtual environment. Repeat for `auth-service`, `task-service`, and `analytics-service`:

**auth-service** (port 8000):

```bash
cd backend/auth-service
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/auth-service/.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost:5432/geofoncier_auth
REDIS_URL=redis://localhost:6379
JWT_PRIVATE_KEY_PATH=../../keys/private.pem
JWT_PUBLIC_KEY_PATH=../../keys/public.pem
```

```bash
uvicorn app.main:app --reload --port 8000
```

**task-service** (port 8001):

```bash
cd backend/task-service
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/task-service/.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost:5433/geofoncier_tasks
REDIS_URL=redis://localhost:6379
AUTH_SERVICE_URL=http://localhost:8000
JWT_PUBLIC_KEY_PATH=../../keys/public.pem
```

```bash
uvicorn app.main:app --reload --port 8001
```

**analytics-service** (port 8002):

```bash
cd backend/analytics-service
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/analytics-service/.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://analytics_ro:analytics_ro@localhost:5433/geofoncier_tasks
REDIS_URL=redis://localhost:6379
AUTH_SERVICE_URL=http://localhost:8000
JWT_PUBLIC_KEY_PATH=../../keys/public.pem
```

```bash
uvicorn app.main:app --reload --port 8002
```

### Step 6 — Start the frontend dev server

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API calls to the local services.

---

## Architecture overview

Three isolated FastAPI services with separate concerns:

- **auth-service** (`:8000`) — user management, RBAC, JWT RS256 issuance, refresh token rotation
- **task-service** (`:8001`) — task CRUD, local JWT verification using auth-service public key
- **analytics-service** (`:8002`) — read-only aggregates, connects to `postgres-tasks` as `analytics_ro`

Key design decisions:
- No cross-schema foreign keys — data integrity enforced at the application layer
- RS256 asymmetric JWT — private key in auth-service only; public key distributed via `/.well-known/jwks.json`
- Redis blacklist for immediate token revocation without waiting for JWT expiry
- Shared library (`lib/geofoncier_shared`) provides JWT middleware, Redis client, and test fixtures

---

## Further reading

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for:
- Common development commands (migrations, tests, linting)
- Testing strategy
- Environment variables reference
- JWT flow details
- Debugging & troubleshooting
- Coding conventions
