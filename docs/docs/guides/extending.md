---
id: extending
title: Extending (recipes)
sidebar_position: 4
---

# Extending

Things the template does **not** include, on purpose, with the shortest path to add each.
The recurring theme: add it as an adapter or a port, never inside `domain/` or `application/`.

## Authentication

Shipped: API keys (`shared/http/auth.py`), `Actor` (`shared/application/actor.py`), and the
"only the organizer can start" rule in `StartTournament`. See
[ADR-009](../decisions/009-authentication-as-adapter).

```bash
API_KEYS='{"s3cret": "alice", "adm1n": "root:admin"}' make run
curl -X POST localhost:8000/api/v1/tournaments -H 'X-API-Key: s3cret' ...
```

To switch to JWT: replace `get_actor` in `shared/http/auth.py` with one that verifies the
bearer token and builds an `Actor` from its claims. Nothing else changes.

## Background jobs / outbox

The in-process bus awaits handlers inside the request. When a handler becomes slow or
unreliable (e-mail, third-party API):

1. Add an `outbox` table and an `OutboxEventPublisher` adapter that *inserts* events in the
   same session as the aggregate (the port stays `EventPublisher`).
2. Add a worker entrypoint (`cleanarch/worker.py`) that polls the outbox and pushes to a
   broker or calls the handlers.
3. Change one line in `bootstrap`. Use cases do not change.

See [ADR-005](../decisions/005-events-in-process) for when this becomes worth it.

## Unit of Work

When one request must modify two aggregates atomically, or a use case must decide when to
commit, introduce a `UnitOfWork` Protocol in `shared/application/ports.py` with
`__aenter__/__aexit__/commit/rollback` and repository attributes, implement it in
`shared/infrastructure/`, and pass it to those use cases instead of a repository.
[ADR-004](../decisions/004-transaction-per-request) explains why it is not there by default.

## Read models / CQRS

If listing endpoints outgrow `repository.list()` (joins, aggregations, search), add a
`TournamentReadModel` Protocol with query-shaped methods returning plain DTOs, implemented
directly with SQL in `infrastructure/`. The write side keeps the repository. You have CQRS
without a bus. [ADR-003](../decisions/003-no-mediator-no-cqrs).

## Caching

A cache is an adapter that wraps another adapter:

```python
class CachedTournamentRepository:
    def __init__(self, inner: TournamentRepository, cache: Redis) -> None: ...
```

Same Protocol, decorated in `bootstrap`.

## Observability

- Structured logging: configure it in `bootstrap` (`logging.config.dictConfig` or `structlog`).
- Tracing/metrics: OpenTelemetry's FastAPI and SQLAlchemy instrumentations are applied in
  `create_app` and `make_engine`; nothing inside the rings changes.
- Request ids: a middleware in `shared/http/`.

## A second driving adapter (CLI, consumer, gRPC)

Create `tournaments/cli/` (or `consumers/`), instantiate use cases the same way
`http/dependencies.py` does, and call `execute`. The architecture tests fail on a folder they do not know: add `cli`
to `RING` in `tests/architecture/test_dependency_rule.py` with position 2 (same ring as
`http`) and the rule applies to it too.

## Multiple features talking to each other

Preferred: through events. Feature B subscribes to Feature A's events in `bootstrap`.
Acceptable: Feature B's use case depends on a port that `bootstrap` implements by calling
Feature A's use case. Forbidden: importing across features (the architecture tests fail).
