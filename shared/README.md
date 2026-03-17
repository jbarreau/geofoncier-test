# geofoncier-shared

Shared utilities for the Geofoncier microservices monorepo.

## Installation

Each service references this package as an editable path dependency:

```toml
# In <service>/pyproject.toml
[tool.poetry.dependencies]
geofoncier-shared = { path = "../shared", develop = true }
```

## Modules

### `geofoncier_shared.fastapi`

FastAPI utilities shared across services.

#### `config_mixin.PublicKeyMixin`

Mixin for `pydantic-settings` `Settings` classes that need to load an RSA
public key (used for RS256 JWT verification).

Provides:
- `jwt_public_key: str` — inline PEM string (env: `JWT_PUBLIC_KEY`)
- `jwt_public_key_path: str` — path to a PEM file (env: `JWT_PUBLIC_KEY_PATH`)
- `public_key_content` property — returns the key from whichever source is set

```python
from geofoncier_shared.fastapi.config_mixin import PublicKeyMixin
from pydantic_settings import BaseSettings

class Settings(PublicKeyMixin, BaseSettings):
    redis_url: str = "redis://localhost:6379"

settings = Settings()
key = settings.public_key_content  # raises ValueError if neither env var is set
```

### `geofoncier_shared.redis`

Async Redis client with a lazy singleton pattern.

#### Functions

| Function | Description |
|----------|-------------|
| `configure(redis_url)` | Set the Redis URL before first use. Call at app startup. |
| `get_redis()` | Return (or lazily create) the shared `aioredis.Redis` instance. |
| `close_redis()` | Close the connection and reset the singleton. Call at app shutdown. |

```python
from geofoncier_shared.redis import configure, get_redis, close_redis

# In FastAPI startup event:
configure(settings.redis_url)

# As a FastAPI dependency:
redis = await get_redis()

# In FastAPI shutdown event:
await close_redis()
```

### `geofoncier_shared.testing`

Pytest fixtures for use in service test suites.

#### `rsa_key_pair` (session-scoped fixture)

Generates a throwaway RSA-2048 key pair. Returns a `dict` with keys
`"private_key"` and `"public_key"` (PEM strings).

Usage in a service's `conftest.py`:

```python
pytest_plugins = ["geofoncier_shared.testing"]
```

## Development

```bash
cd shared
poetry install --with dev
poetry run pytest --cov=geofoncier_shared --cov-report=term-missing
poetry run black --check .
```
