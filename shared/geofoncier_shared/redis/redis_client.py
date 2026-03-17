import redis.asyncio as aioredis

_client: aioredis.Redis | None = None
_redis_url: str = "redis://localhost:6379"


def configure(redis_url: str) -> None:
    """Call once at app startup before first get_redis() call."""
    global _redis_url
    _redis_url = redis_url


async def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(_redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None
