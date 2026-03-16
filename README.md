# README.md

## Quick Start

### Prerequisites

- Docker & docker-compose (Docker Desktop ≥ 4.x)

### Launch

```bash
# First run: builds images, generates RSA keys, runs migrations, seeds the DB
docker compose up --build

# Subsequent runs (no rebuild needed)
docker compose up
```

The startup sequence is automatic:

1. **keygen** — generates an RSA-2048 key pair into a named Docker volume (`jwt_keys`). Skipped on subsequent runs.
2. **migrate** — runs `alembic upgrade head` for `auth-service`. Idempotent.
3. **seed** — inserts default roles, permissions, and users. Idempotent.
4. **auth-service / task-service / analytics-service** — start once the above complete.

### Default accounts (seed data)

| Email | Password | Role |
|---|---|---|
| admin@geofoncier.local | admin123 | admin |
| user@geofoncier.local | user123 | user |
| viewer@geofoncier.local | viewer123 | viewer |

### Service URLs

| Service | URL |
|---|---|
| auth-service | http://localhost:8000 |
| task-service | http://localhost:8001 |
| analytics-service | http://localhost:8002 |

---

## Mock Data (optional)

Insert ~20 fake users to populate the database for front-end development:

```bash
# One-shot run against the running stack
docker compose --profile mock run --rm mock-data
```

All mock accounts share the password `password123` and are assigned `user` or `viewer` roles.
Email format: `firstname.lastnameN@mock.geofoncier.local`

To add more mock data, simply re-run the command — it skips already-existing emails.

You can also run the script directly (requires Python 3.12 + auth-service deps):

```bash
cd auth-service
source venv/bin/activate
DATABASE_URL=postgresql+asyncpg://geofoncier:geofoncier@localhost/geofoncier \
    python ../scripts/mock_data.py
```

---

## Project Overview

**Geofoncier – Test technique**: Task management application with user and permission management. This is a Senior Backend/Fullstack technical assessment featuring three independent FastAPI services coordinated via docker-compose.

## Architecture

Three isolated FastAPI services with separate concerns:

- **auth-service** – User management, role-based access control (RBAC), JWT issuance (RS256), refresh token rotation
- **task-service** – CRUD operations for tasks, local JWT verification using public key
- **analytics-service** – Read-only service for aggregates and statistics

### Key Architectural Patterns

- **Separation of concerns**: Each service owns its database schema and business logic
- **No cross-schema foreign keys**: Data integrity enforced via application logic, not SQL constraints
- **JWT-based auth**: RS256 asymmetric signing (private key in auth-service, public key distributed to other services)
- **Token revocation**: Redis blacklist for immediate logout/ban without waiting for JWT expiry
- **Token rotation**: Refresh tokens are hashed in DB and rotated on each use
- **Service isolation**: Services communicate only through public APIs, no shared internal contracts

### Data Model Separation

- PostgreSQL schema `auth`: users, roles, permissions, refresh tokens, role assignments
- PostgreSQL schema `tasks`: tasks table and task-related entities
- Redis: JWT blacklist entries (user_id, expires at)
- No application-level sharing of ORM models between services

## Development Setup

### Prerequisites

- Python 3.12
- PostgreSQL 16
- Redis 7+
- Docker & docker-compose

### Service Structure

Each service follows this structure:

```
{service-name}/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic v2 request/response schemas
│   ├── routes/                 # API endpoint definitions
│   ├── dependencies.py         # FastAPI dependency injection
│   ├── exceptions.py           # Custom exceptions
│   └── services/               # Business logic layer
├── migrations/                 # Alembic migrations (alembic/)
├── tests/
│   ├── conftest.py            # pytest fixtures
│   ├── test_*.py              # Test files matching test discovery
│   └── integration/           # Cross-service tests
├── requirements.txt
├── .env.example               # Environment variables template
└── Dockerfile
```

## Common Commands

### Environment Setup

```bash
# Create and activate venv for a service
cd auth-service
python3.12 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Database & Migrations

```bash
# Run all migrations for auth-service (from service directory)
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Add column to users"

# Check migration status
alembic current
```

### Running Services Locally

```bash
# Start all services with docker-compose (from repo root)
docker-compose up

# Start specific service
docker-compose up auth-service

# Rebuild images (after requirements.txt changes)
docker-compose up --build

# Run service locally in venv (useful for debugging)
cd auth-service && uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
# Run all tests for a service
cd auth-service
pytest

# Run specific test file
pytest tests/test_auth.py

# Run specific test function
pytest tests/test_auth.py::test_user_creation

# Run with coverage
pytest --cov=app tests/

# Run integration tests
pytest tests/integration/

# Watch mode (if pytest-watch installed)
ptw
```

### Code Quality

```bash
# Format code (if using ruff/black)
# Install: pip install ruff
ruff format app/

# Lint
ruff check app/

# Type checking
mypy app/
```

## Important Implementation Details

### JWT Flow (auth-service)

1. **User login**: verify credentials → create access token (15 min TTL) + refresh token (7 days)
2. **Refresh token storage**: Hash with bcrypt, store in DB, include version in JWT to detect invalidation
3. **Token claims**: `user_id`, `roles[]`, `permissions[]`, `exp`, `iat`, `jti` (unique token ID)
4. **Public key distribution**: auth-service exposes `/auth/.well-known/jwks.json` for public key retrieval

### JWT Verification (task-service, analytics-service)

1. Fetch and cache auth-service's public key on startup
2. Verify JWT signature, expiry, claims structure
3. Check Redis blacklist for revoked tokens (by JTI or user_id)
4. Extract user_id and permissions from claims

### Environment Variables

Each service needs a `.env` file (never committed). See `.env.example` in each service folder:

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost/geofoncier_auth
REDIS_URL=redis://localhost:6379
AUTH_SERVICE_URL=http://auth-service:8000  # For other services
JWT_PRIVATE_KEY_PATH=./keys/private.pem   # auth-service only
JWT_PUBLIC_KEY_PATH=./keys/public.pem     # for all services
LOG_LEVEL=INFO
```

### Service Communication

- **Synchronous**: Direct HTTP calls (httpx) for real-time verification
- **Cross-service auth**: task-service calls auth-service only during startup to load public key and possibly for user/role info
- **No pub/sub**: Services don't subscribe to each other's events (by design – read-only analytics)

## Debugging & Troubleshooting

### Common Issues

**JWT verification fails**:

- Check that auth-service public key is being fetched correctly
- Verify token was signed with auth-service's private key
- Check token expiry and Redis blacklist

**Database schema mismatch**:

- Run pending migrations: `alembic upgrade head`
- Check migration files for cross-schema references (should not exist)

**Service-to-service communication fails**:

- Verify service URLs in .env (especially in docker-compose)
- Check service is actually running: `docker-compose ps`
- Look at container logs: `docker-compose logs auth-service`

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f task-service

# Last 100 lines
docker-compose logs --tail=100 auth-service
```

## Testing Strategy

- **Unit tests**: Individual functions, mocked dependencies (DB, Redis, other services)
- **Integration tests**: Full request-response cycles within a service, real DB/Redis
- **Cross-service tests**: API calls between services, full docker-compose stack
- **Fixtures**: Use `conftest.py` for reusable test fixtures (DB session, JWT tokens, users)

### Test Database

Tests should use an isolated test database. Configure in `conftest.py`:

```python
@pytest.fixture
def db_session(engine):
    # Create test tables
    # Yield session
    # Cleanup
```

## Conventions

- **Imports**: Organize as stdlib → third-party → local, alphabetical within groups
- **Type hints**: Use Python 3.12+ syntax (no `from typing import ...`, use `list[str]` not `List[str]`)
- **Async/await**: All database and Redis operations must be async
- **Error handling**: Custom exceptions in `app/exceptions.py`, HTTP status codes in routes
- **Commit messages**: English, imperative mood, < 72 chars first line
- **Variable naming**: snake_case for variables/functions, PascalCase for classes

## Before Submitting Work

1. Run all tests and ensure they pass: `pytest`
2. Verify services can start: `docker-compose up --build`
3. Check no hardcoded secrets or .env files are staged: `git diff --cached`
4. Run code formatting/linting if configured
5. Write commit messages in English, imperative, concise
