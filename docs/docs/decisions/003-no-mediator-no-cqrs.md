---
id: 003-no-mediator-no-cqrs
title: "ADR-003: No mediator, no CQRS bus"
---

# ADR-003: No mediator, no command/query bus

**Status:** accepted

## Context

The previous iteration routed every command and query through a global `Mediator` with
handlers registered by decorator at import time (`@mediator.command(...)`), which required
`import handlers  # noqa` in the bootstrap for the side effect. It also split every operation
into command class + handler + view model.

MediatR-style buses solve real problems - cross-cutting pipelines (logging, validation,
transactions), decoupled handlers, many entrypoints - at the cost of indirection you cannot
follow with "go to definition".

## Decision

- A use case is a class with a constructor and an `execute` method. The router calls it.
- A command object exists only when an operation has several input fields
  (`CreateTournamentCommand`). Single-id operations take the id.
- Reads and writes go through the same repository until a read genuinely needs a different
  shape (then: a read-model port, see [Extending](../guides/extending)).

## Consequences

- Every call is explicit and greppable; a new reader can trace a request in one sitting.
- Cross-cutting concerns are handled where they belong: transactions in the session
  dependency, error mapping in `shared/http/errors.py`, logging in the event bus.
- No handler registry, no import-order magic, no "no handler found" runtime error.

## When to revisit

- Several entrypoints (HTTP, CLI, consumers) dispatch the same commands and you want one
  pipeline of behaviours around all of them.
- You need a persistent audit of every command executed.
- Reads dominate and their shape diverges from the aggregates: add read models first;
  a bus is still optional.

## Proof

No executable proof: the decision is the absence of a pattern. There is no runtime property
to falsify; use cases being plain classes is visible in `application/use_cases.py`.
