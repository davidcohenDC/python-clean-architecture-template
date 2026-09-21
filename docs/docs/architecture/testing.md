---
id: testing
title: Testing
sidebar_position: 5
---

# Testing

The template is opinionated about the **architecture**, not about how your team tests.
Organise tests by ring, by feature, next to the code, TDD or not - nothing in the template
depends on the folder layout. What it gives you:

- `pytest` with async support and a few fixtures in `tests/conftest.py`: `client` (the real
  app with in-memory adapters), `make_settings` (ignores your `.env`), a recording event
  publisher, a fixed clock;
- the **dependency rule as a tool**, not a test: `scripts/archcheck.py check` runs in
  `make check` and in CI whatever your tests look like;
- tests for what you **inherit** (`tests/http`, `tests/bootstrap`): error envelope, request
  ids, probes, the transaction/event unit of work - written against stub sessions and
  throwaway routes, so they need no feature at all;
- a worked **example** of how one feature can be tested at every level (`tests/tournaments`),
  removed with the example.

```bash
make test        # everything, with coverage
make test-fast   # without the slow contract tests (-m "not contract")
make check       # lint, types, architecture, tests: what CI runs
```

## The example, level by level

`tests/tournaments/` shows one way to cover a feature. Steal what you like:

| File | Level | Depends on |
|---|---|---|
| `test_phases.py`, `test_progress.py`, `test_tournament.py` | domain rules | nothing |
| `test_use_cases.py` | use cases with the in-memory adapter and fakes | nothing |
| `test_repository_contract.py` | one contract for every adapter, incl. concurrency | SQLite (or PostgreSQL via `TEST_DATABASE_URL`) |
| `test_api.py`, `test_auth.py`, `test_errors.py` | HTTP boundary | in-memory adapters |
| `test_transaction.py`, `test_events.py` | commit/event semantics through real HTTP | SQLite file |
| `test_cli.py` | the CLI adapter | SQLite file |

Because aggregates are immutable and events are values, most assertions are equalities:

```python
assert result.events == (TournamentStarted(tournament.id),)
```

Use cases receive the **real** in-memory repository, not a mock. If a use case is hard to
test this way, its dependencies are probably not going through ports.

## The repository contract

`test_repository_contract.py` is parametrised over the in-memory and the SQLAlchemy
repository and runs the *same* tests on both, including the optimistic-concurrency race
(two readers, one row, the second writer must get `ConflictError`). When you add an adapter,
add it to the fixture's `params`. When you scaffold a feature, copy the file.

## What you inherit is tested without you

- `tests/http/test_errors.py`, `test_ops.py`: unknown route, wrong method, unexpected
  exception, request id on every response, `/health`, `/ready`.
- `tests/bootstrap/test_unit_of_work.py`: commit before the response, rollback on error,
  failed commit → 500, event handlers after commit, failing handler logged - on a stub
  session and a throwaway route, no feature involved.

## Architecture: a tool, and optionally a test

`scripts/archcheck.py` walks the package with `ast` and reports every import that points
outward, every cross-feature import, every third-party import in `domain`/`application`,
every module in an unknown ring (`check`); it also draws the real dependency graph
(`graph`). `tests/architecture/test_dependency_rule.py` is the one-line pytest wrapper, for
IDEs that only run tests. The checker's own self-check (fifteen deliberate violations that
must be caught) lives in the template repository, not in your project.
