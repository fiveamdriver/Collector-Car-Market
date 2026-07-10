from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.models  # noqa: F401 — registers SQLAlchemy models with Base.metadata
from app.config import CORS_ORIGINS
from app.database import engine, init_db
from app.routers import listings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Collector Car Market API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],  # the API is read-only; all writes happen via backend/data scripts
    allow_headers=["*"],
)

app.include_router(listings.router, prefix="/api/v1")


@app.get("/health")
async def health(response: Response) -> dict[str, str]:
    """Liveness + DB reachability, so a dead connection pool fails the check."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
