"""Configuration, read once from the environment (and ``.env`` in development).

Settings are an *outer ring* concern. Nothing in ``domain`` or ``application``
imports this module: if a use case needs a value, it receives it explicitly.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cleanarch.shared.application.actor import Actor

MEMORY_DATABASE_URL = "memory://"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "python-clean-architecture-template"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        description=(
            "Any SQLAlchemy async URL, or 'memory://' to run with in-memory adapters "
            "(no database, nothing persisted between restarts)."
        ),
    )
    database_echo: bool = False

    api_keys: dict[str, str] = Field(
        default_factory=dict,
        description=(
            'JSON object mapping an API key to an actor: {"s3cret": "alice", '
            '"adm1n": "root:admin"}. Roles follow the id after a colon, comma-separated. '
            "Empty (the default) disables authentication: everyone is 'anonymous'."
        ),
    )

    @property
    def actors(self) -> dict[str, Actor]:
        table: dict[str, Actor] = {}
        for key, spec in self.api_keys.items():
            actor_id, _, roles = spec.partition(":")
            table[key] = Actor(actor_id, frozenset(r for r in roles.split(",") if r))
        return table

    @property
    def use_in_memory(self) -> bool:
        return self.database_url == MEMORY_DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()
