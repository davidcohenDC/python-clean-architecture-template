---
id: change-database
title: Change the database
sidebar_position: 3
---

# Change the database

## Another SQL database: change the URL

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db      # asyncpg ships in the `postgres` extra
DATABASE_URL=mysql+aiomysql://user:pass@host:3306/db          # uv add aiomysql
DATABASE_URL=sqlite+aiosqlite:///./dev.db                     # default
```

The SQLAlchemy adapter, the migrations and the tests are dialect-agnostic
(`render_as_batch=True` in `alembic/env.py` keeps SQLite happy with `ALTER TABLE`).
CI runs the integration tests and migrations on PostgreSQL 17.

## No database: `memory://`

```bash
DATABASE_URL=memory://
```

`bootstrap` wires the in-memory adapters; nothing is persisted between restarts. Good for
demos, front-end development against a fake backend, and the API tests.

## A different technology (MongoDB, DynamoDB, an HTTP service...)

The domain and application rings do not change. You write one adapter and one line of wiring:

1. `tournaments/infrastructure/mongo.py`:

    ```python
    class MongoTournamentRepository:
        def __init__(self, collection: AsyncIOMotorCollection) -> None: ...
        async def add(self, tournament: Tournament) -> None: ...
        async def get(self, tournament_id: TournamentId) -> Tournament | None: ...
        async def save(self, tournament: Tournament) -> None: ...
        async def list(self, *, limit: int, offset: int) -> Sequence[Tournament]: ...
    ```

    mypy checks it against the `TournamentRepository` Protocol - no inheritance needed.

2. A mapping between the aggregate and the document, next to it (`mongo_mapping.py`).

3. In `bootstrap/features/tournaments.py`, replace the SQLAlchemy branch of `wire_http` (or
   add a third branch on a setting). Whatever owns the connection lifecycle goes in `lifespan`.

4. Copy the repository contract test of the example (`tests/tournaments/test_repository_contract.py`)
   and add the new adapter to its `params`. The assertions stay identical: that is the
   contract every adapter must satisfy.

## Swapping the ORM itself

`shared/infrastructure/database.py` (engine, session, `transaction()`) and
`tournaments/infrastructure/sqlalchemy/` are the only places that import SQLAlchemy;
`alembic/` is the only place that depends on it for migrations. Replace those, keep
everything else.
