---
id: 002-no-di-library
title: "ADR-002: No DI library"
---

# ADR-002: No dependency-injection library

**Status:** accepted

## Context

The previous iteration of this codebase had a hand-rolled container resolved from inside use
cases (`container.resolve(UnitOfWork)`), i.e. a service locator: use cases could not be
constructed with fakes without touching global state. Popular alternatives are
`dependency-injector`, `dishka`, `lagom`, `punq`.

Any library is one more thing a fork must learn before understanding the architecture.

## Decision

- Use cases take their ports as **constructor arguments**. Nothing else.
- Each feature declares its ports as **placeholder dependencies** (functions that raise
  `NotImplementedError`) in `http/dependencies.py`, and builds use cases from them with
  `Depends`.
- `bootstrap/app.py` is the **composition root**: it overrides the placeholders with real
  providers via `app.dependency_overrides`, choosing adapters from settings.
- Tests override the same placeholders with fakes.

## Consequences

- Zero new concepts: `Depends` is FastAPI's own mechanism, `dependency_overrides` is its
  documented testing hook.
- All wiring is in one file that reads top-to-bottom.
- Constructor injection makes use-case tests trivial: `StartTournament(repo, events)`.
- The placeholder-raises-if-not-overridden trick is the one piece of indirection; it fails
  loudly at first request rather than silently.
- A non-HTTP entrypoint (CLI, worker) must build use cases itself, the same way
  `http/dependencies.py` does. For a handful of use cases that is a few lines; if it grows
  past that, extract the factories into `bootstrap/factories.py`.

## When to revisit

If the object graph gets deep (use cases depending on services depending on services) and
the factories in `dependencies.py` become the bulk of the file, a lightweight container
(`dishka` integrates with FastAPI cleanly) can replace the placeholders without touching
`application/`.
