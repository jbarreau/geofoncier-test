from fastapi import FastAPI

from .redis_client import close_redis

app = FastAPI(title="task-service")


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_redis()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
