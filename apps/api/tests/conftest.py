from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from treasurfy.config import Settings
from treasurfy.main import create_app


@pytest.fixture
def client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    application = create_app(
        Settings(database_url="sqlite+pysqlite://", seed_demo=True),
        engine=engine,
    )

    with TestClient(application) as test_client:
        yield test_client
