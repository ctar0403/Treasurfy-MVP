from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from treasurfy.api import router
from treasurfy.config import Settings
from treasurfy.database import Database, create_database_engine
from treasurfy.seed import seed_demo_data


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    initialize_database: bool = True,
    defer_database: bool = False,
) -> FastAPI:
    application_settings = settings or Settings.from_environment()
    database = (
        None
        if defer_database
        else Database(
            engine or create_database_engine(application_settings.database_url)
        )
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if initialize_database and database is not None:
            database.create_schema()
            if application_settings.seed_demo:
                with database.session_factory() as session:
                    seed_demo_data(session)
        yield

    application = FastAPI(
        title="TreasurFy API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database = database

    @application.middleware("http")
    async def add_api_safety_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-ID"] = str(uuid4())
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(application_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-User-ID"],
    )
    application.include_router(router)
    return application


app = create_app()
