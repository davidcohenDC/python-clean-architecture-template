---
id: 004-transaction-per-request
title: "ADR-004: Transaction per request, no Unit of Work"
---

# ADR-004: One transaction per request; no Unit of Work abstraction

**Status:** accepted

## Context

Unit of Work (UoW) is the standard answer to "who commits?". It gives use cases a context
manager with repositories attached and explicit `commit()`. The previous iteration had one,
mixed with an outbox and an event bus, and it was the hardest part of the code to explain.

In this template every use case touches **one aggregate** and runs inside **one HTTP
request**.

## Decision

- `bootstrap/transaction.py` has a `TransactionMiddleware` that opens one session per
  request, exposes it as `request.state.session`, and **commits before the response is
  sent**: status `< 400` → commit, `>= 400` or exception → rollback, failed commit →
  rollback + `500 TransactionFailed`.
- `bootstrap.get_session` is the FastAPI dependency that hands that session to the
  repository providers; all repositories in a request share it.
- Repositories `flush()` and never `commit()`.
- Use cases know nothing about transactions.
- `shared/infrastructure/database.transaction()` is the same guarantee as a context manager,
  for CLI/worker entrypoints that have no request.

Why a middleware and not a `yield` dependency? Since FastAPI 0.118 the exit code of a
`yield` dependency runs *after* the response has been sent. A commit there can fail while
the client already holds a `201`. We hit exactly that in review; `tests/api/test_transaction.py`
now proves a failed commit is a `500` and persists nothing.

## Consequences

- Use cases stay four lines and have one fewer dependency.
- Atomicity holds per request: if publishing an event raises, the write is rolled back;
  if the commit itself fails, the client gets a `500`, never a false success.
- The in-memory adapter needs no transaction concept at all, which keeps application tests
  free of fixtures.
- A use case cannot commit halfway or run two independent transactions. That is a feature
  until it isn't.

## When to revisit

Introduce a `UnitOfWork` port ([recipe](../guides/extending#unit-of-work)) when:

- one operation must update two aggregates atomically and you want that visible in the use
  case rather than implied by the request;
- use cases run outside HTTP (workers, CLI) and there is no request to scope the session to;
- you need to commit *before* publishing to an external system.
