---
id: testing
title: Testing
sidebar_position: 5
---

# Testing

The test suite mirrors the rings. Each folder answers one question, with one set of tools.

| Folder | Question | Depends on | Speed |
|---|---|---|---|
| `tests/domain` | Are the business rules right? | nothing | ms |
| `tests/application` | Do use cases orchestrate correctly? | in-memory adapter, recording publisher | ms |
| `tests/integration` | Does the SQL adapter round-trip the aggregate? | SQLite (or PostgreSQL) | ~100 ms |
| `tests/api` | Is the HTTP contract right, are errors mapped? | full app, in-memory adapters | ~10 ms |
| `tests/architecture` | Does the code still respect the Dependency Rule? | the source tree | ms |

```bash
make test-fast   # domain + application + architecture: what the pre-commit hook runs
make test        # everything, with coverage
```

## Domain tests

Plain functions and classes, no fixtures beyond a couple of builders in `tests/conftest.py`:

```python
def test_cannot_start_twice():
    started = make_tournament().start().aggregate
    with pytest.raises(TournamentAlreadyStarted):
        started.start()
```

Because aggregates are immutable and events are values, assertions are equality checks:

```python
assert result.events == (TournamentStarted(tournament.id),)
```

`event_id` and `occurred_at` are excluded from equality (`compare=False`) precisely to allow this.

## Application tests

Use cases receive the **real** `InMemoryTournamentRepository` (it ships in `infrastructure/`)
and a tiny `RecordingEventPublisher` fake:

```python
async def test_domain_error_leaves_state_and_events_untouched(repository, events):
    await repository.add(make_tournament(id="t-1").start().aggregate)
    with pytest.raises(TournamentAlreadyStarted):
        await StartTournament(repository, events).execute(TournamentId("t-1"))
    assert events.events == []
```

No `unittest.mock`, no patching. If a use case is hard to test this way, its dependencies
are probably not going through ports.

## Integration tests

Only the adapter is under test. A fresh schema is created per test on SQLite in-memory;
set `TEST_DATABASE_URL` to run the same file against PostgreSQL (CI does).

```python
await repository.add(tournament); await session.commit(); session.expunge_all()
assert await repository.get(TournamentId("t-1")) == tournament
```

The `expunge_all()` is the point: it forces a real re-read so the mapping is tested, not the
identity map.

## API tests

`create_app(Settings(database_url="memory://"))` gives the real app with in-memory adapters,
driven through `httpx.AsyncClient` and `ASGITransport`. They cover routing, validation,
serialisation and the error envelope. `tests/api/test_transaction.py` is the exception: it
runs the real SQLite path end to end and proves that a `422` rolls back and that a failed
commit is a `500` with nothing persisted - the guarantee of ADR-004.

## Architecture tests

`tests/architecture/test_dependency_rule.py` walks `src/cleanarch` with `ast`, no imports
executed, and checks three things for every module:

1. it imports only from its own ring or an inner one (`infrastructure` and `http` may not
   import each other);
2. `domain` and `application` import only the standard library and this package - no
   `fastapi`, `pydantic`, `sqlalchemy`, `httpx`...;
3. features never import other features, and `shared` never imports a feature.

The failure message says what to do:

```text
cleanarch.tournaments.domain.tournament (domain) imports
cleanarch.tournaments.infrastructure.sqlalchemy (infrastructure):
'infrastructure' is an outer ring. Invert the dependency with a port.
```

It is deliberately hand-written (about 100 lines) rather than pulled from a library so that
the rule is *readable* in the repository, and it runs in the pre-commit hook and in CI.
