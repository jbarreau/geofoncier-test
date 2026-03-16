from fastapi import FastAPI

from .database import engine
from .redis_client import close_redis
from .routes.tasks import router as tasks_router

app = FastAPI(title="task-service")

app.include_router(tasks_router)


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_redis()
    await engine.dispose()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
