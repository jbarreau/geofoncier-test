# Development Guide

Reference documentation for working on the Géofoncier codebase.

---

## Project structure

```
.
├── backend/
│   ├── auth-service/       # User management, RBAC, JWT issuance
│   ├── task-service/       # Task CRUD
│   ├── analytics-service/  # Read-only aggregates
│   └── test_e2e/           # End-to-end tests (requires full stack)
├── frontend/               # Vue 3 + Vite + Pinia
├── lib/                    # Shared Python library (geofoncier_shared)
├── scripts/                # seed.py, mock_users.py, mock_tasks.py
├── init-db/                # PostgreSQL init scripts (analytics_ro user)
├── openapi/                # Generated OpenAPI specs
└── docker-compose.yml
```

### Service structure

Each backend service follows the same layout:

```
{service-name}/
├── app/
│   ├── main.py             # FastAPI app, lifespan hooks
│   ├── config.py           # pydantic-settings Settings class
│   ├── database.py         # Async SQLAlchemy engine + session
│   ├── dependencies.py     # FastAPI dependency injection
│   ├── exceptions.py       # Custom HTTP exceptions
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic v2 request/response schemas
│   ├── routes/             # API endpoint definitions
│   └── services/           # Business logic layer
├── migrations/             # Alembic migrations (auth-service, task-service only)
├── tests/                  # pytest unit + integration tests
├── requirements.txt
└── Dockerfile
```

---

## Common commands

### Migrations

```bash
# Run pending migrations (from service directory, with venv active)
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Add column to users"

# Check current migration state
alembic current

# Downgrade one step
alembic downgrade -1
```

### Running tests

```bash
# All tests for a service
cd backend/auth-service
pytest

# Specific file
pytest tests/test_auth.py

# Specific test
pytest tests/test_auth.py::test_user_creation

# With coverage
pytest --cov=app tests/

# Frontend unit tests
cd frontend
npm test

# E2E tests (requires full docker compose stack to be running)
cd backend/test_e2e
pytest
```

### Code quality

```bash
# Format Python code
ruff format app/

# Lint Python code
ruff check app/

# Type checking
mypy app/

# Frontend lint
cd frontend && npm run lint
```

### Docker

```bash
# Start full stack
docker compose up --build

# Start only infrastructure (postgres + redis)
docker compose up postgres-auth postgres-tasks redis

# View logs
docker compose logs -f
docker compose logs -f auth-service

# Rebuild a single service
docker compose up --build auth-service

# Remove volumes (full reset)
docker compose down -v
```

---

## Testing strategy

- **Unit tests** (`backend/{service}/tests/`) — individual functions, mocked DB/Redis/external services
- **Integration tests** (`backend/{service}/tests/integration/`) — full request-response cycles within a service, real DB and Redis
- **E2E tests** (`backend/test_e2e/`) — API calls across services against a running docker compose stack
- **Frontend tests** (`frontend/src/**/*.test.ts`, `*.spec.ts`) — Vitest + Vue Test Utils component tests

Test fixtures are defined in `conftest.py` at each level. The shared library provides an `rsa_key_pair` session-scoped pytest fixture for generating RSA-2048 keys in tests.

### Test database

Each service's integration tests use a separate test database. Configure in `conftest.py`:

```python
@pytest.fixture
async def db_session(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

---

## Environment variables

Each service reads its configuration from environment variables (or a `.env` file, never committed).

### auth-service

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis URL (`redis://localhost:6379`) |
| `JWT_PRIVATE_KEY_PATH` | Path to RSA private key (PEM) |
| `JWT_PUBLIC_KEY_PATH` | Path to RSA public key (PEM) |

### task-service

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL for `geofoncier_tasks` |
| `REDIS_URL` | Redis URL |
| `AUTH_SERVICE_URL` | Base URL of auth-service (e.g. `http://localhost:8000`) |
| `JWT_PUBLIC_KEY_PATH` | Path to RSA public key (PEM) |

### analytics-service

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL for `geofoncier_tasks` (read-only user) |
| `REDIS_URL` | Redis URL |
| `AUTH_SERVICE_URL` | Base URL of auth-service |
| `JWT_PUBLIC_KEY_PATH` | Path to RSA public key (PEM) |

---

## JWT flow

### auth-service (issuer)

1. User logs in → verify credentials (bcrypt)
2. Issue **access token** (RS256, 15 min TTL) with claims: `user_id`, `email`, `roles[]`, `permissions[]`, `jti`, `iat`, `exp`
3. Issue **refresh token** (7 day TTL) — raw token embeds `db_id` for O(1) DB lookup; hashed version stored in DB
4. Public key available at `GET /.well-known/jwks.json`

### task-service / analytics-service (verifiers)

1. Fetch auth-service public key on startup (via `JWT_PUBLIC_KEY_PATH` or JWKS endpoint)
2. On each request: verify JWT signature (RS256), expiry, and claims structure
3. Check Redis blacklist by `jti` — rejects tokens that have been explicitly revoked
4. Extract `user_id`, `roles`, `permissions` from claims via `geofoncier_shared.fastapi.middleware.jwt`

### Token revocation

- **Logout**: access token JTI is added to Redis blacklist; refresh token is marked `revoked=true` in DB
- **TTL**: blacklist entries expire automatically when the access token would have expired

---

## Debugging & troubleshooting

### JWT verification fails

- Ensure auth-service is running and the public key path is correct
- Verify the token was signed with the same private key as the public key being used
- Check Redis is reachable (blacklist lookups fail open by default if Redis is down — check service logs)

### Database schema mismatch

```bash
# Check pending migrations
alembic current
alembic history

# Apply pending migrations
alembic upgrade head
```

### Service-to-service communication fails

```bash
# Check all services are healthy
docker compose ps

# Inspect logs
docker compose logs auth-service
docker compose logs task-service

# Verify network connectivity (inside containers)
docker compose exec task-service curl http://auth-service:8000/health
```

### Port conflicts

Default ports: auth `8000`, task `8001`, analytics `8002`, postgres-auth `5432`, postgres-tasks `5433`, redis `6379`, frontend `80`.

---

## Coding conventions

- **Python imports**: stdlib → third-party → local, alphabetical within groups
- **Type hints**: Python 3.12+ syntax — `list[str]`, `dict[str, int]`, `X | None` (no `from typing import`)
- **Async**: all database and Redis operations must be `async` / `await`
- **Error handling**: raise custom exceptions from `app/exceptions.py`; map to HTTP status codes in routes
- **Permissions**: always use plural prefix — `tasks:create`, `tasks:read`, `users:manage`, `analytics:read`
- **Variable naming**: `snake_case` for variables/functions, `PascalCase` for classes
- **Commit messages**: English, imperative mood, < 72 chars first line (Conventional Commits)

---

## Before submitting work

1. Run all tests: `pytest` (per service) and `cd frontend && npm test`
2. Verify the full stack starts: `docker compose up --build`
3. Check no secrets or `.env` files are staged: `git diff --cached`
4. Run linting: `ruff check app/` and `mypy app/`
5. Write commit messages in English, imperative, concise
