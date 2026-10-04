from __future__ import annotations

from contextlib import asynccontextmanager

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
) -> FastAPI:
    application_settings = settings or Settings.from_environment()
    database = Database(
        engine or create_database_engine(application_settings.database_url)
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
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
