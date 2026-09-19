"""SQLAlchemy plumbing shared by every SQL adapter.

Only *mechanics* live here (engine, session factory, declarative base).
Tables and mappers belong to the feature that owns them.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every persistence model in the project."""


def make_engine(url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(url, echo=echo, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def transaction(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """One session == one transaction, for non-HTTP entrypoints (CLI, workers, scripts).

    Commit if the block succeeds, roll back otherwise. HTTP requests use
    ``bootstrap.transaction.TransactionMiddleware`` instead, which commits before
    the response is sent. Use cases never call ``commit()`` themselves (ADR-004).
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
