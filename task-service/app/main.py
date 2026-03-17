from fastapi import FastAPI

from .redis_client import close_redis, configure

app = FastAPI(title="task-service")


@app.on_event("startup")
async def startup() -> None:
    from .config import settings

    configure(settings.redis_url)


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_redis()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
