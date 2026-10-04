from __future__ import annotations

import os
from dataclasses import dataclass


def _environment_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite+pysqlite:///./treasurfy.db"
    seed_demo: bool = True
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )

    @classmethod
    def from_environment(cls) -> "Settings":
        configured_origins = os.getenv("TREASURFY_CORS_ORIGINS")
        origins = (
            tuple(
                origin.strip()
                for origin in configured_origins.split(",")
                if origin.strip()
            )
            if configured_origins is not None
            else cls.cors_origins
        )
        return cls(
            database_url=os.getenv(
                "TREASURFY_DATABASE_URL", cls.database_url
            ),
            seed_demo=_environment_flag("TREASURFY_SEED_DEMO", True),
            cors_origins=origins,
        )
