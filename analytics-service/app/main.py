from contextlib import asynccontextmanager

from fastapi import FastAPI

from geofoncier_shared.redis.redis_client import close_redis, configure

from .database import close_db
from .routes.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .config import settings

    configure(settings.redis_url)
    yield
    await close_redis()
    await close_db()


app = FastAPI(title="Analytics Service", lifespan=lifespan)

app.include_router(analytics_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
