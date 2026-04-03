from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import init_db


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.is_production and settings.is_sqlite:
        raise RuntimeError("Production requires PostgreSQL via DATABASE_URL; SQLite is only supported for local development")
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


from sqlalchemy import inspect

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    print("DB URL:", engine.url)
    print("TABLES:", inspector.get_table_names())
    print("SEED COLUMNS:", [c["name"] for c in inspector.get_columns("seed_restaurants")])


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="/api/v1")


