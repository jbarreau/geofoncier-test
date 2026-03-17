from fastapi import FastAPI

from .redis_client import close_redis, configure
from .routes import auth_router

app = FastAPI(title="auth-service")


@app.on_event("startup")
async def startup() -> None:
    from .config import settings

    configure(settings.redis_url)
    # Fail fast at startup if JWT keys are not configured
    _ = settings.private_key_content
    _ = settings.public_key_content


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_redis()


app.include_router(auth_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
