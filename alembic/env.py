"""Alembic environment (async). Reads DATABASE_URL through the app settings."""

import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from cleanarch.bootstrap.settings import get_settings
from cleanarch.shared.infrastructure.database import Base

# isort: split
# Import every persistence model so that ``autogenerate`` sees its table.
# >>> example: tournaments
import cleanarch.tournaments.infrastructure.sqlalchemy.models  # noqa: F401

# <<< example: tournaments

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
if settings.use_in_memory:
    print("DATABASE_URL=memory:// uses in-memory adapters: nothing to migrate.", file=sys.stderr)
    sys.exit(0)
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(config.get_section(config.config_ini_section, {}))
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
