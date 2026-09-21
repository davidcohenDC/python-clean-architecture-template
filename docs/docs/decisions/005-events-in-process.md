---
id: 005-events-in-process
title: "ADR-005: Domain events in-process"
---

# ADR-005: Domain events are values, dispatched in-process

**Status:** accepted

## Context

Immutable aggregates cannot append to a private `_events` list. The previous iteration
solved this with `DomainResult` (aggregate + events) - a good idea - and then shipped three
buses (local, Redis Streams, webhook), a SQL outbox, a Mongo outbox and a worker, none of
which the example needed.

## Decision

- Domain methods return `DomainResult(aggregate, events)`. Events are frozen dataclasses
  carrying primitives; `event_id` and `occurred_at` are excluded from equality.
- The application ring has one port, `EventPublisher.publish(events)`. Publishing
  **records** events in the current unit of work; it does not run anything.
- `bootstrap` dispatches the recorded events **after the transaction committed**
  (`EventDispatchMiddleware` for HTTP, the same two steps in `bootstrap/cli.py`), through
  `InProcessEventBus`, sequentially, in publication order. Subscribers are registered by
  each feature's `subscribe(bus)` hook in `bootstrap/features/`.
- No outbox, no broker, no background tasks.

## Consequences

- Events are testable as values: `assert result.events == (TournamentStarted(id),)`.
- A handler that reads the database sees the **committed** state (it may open its own
  session). Verified in `tests/tournaments/test_events.py` on a SQLite file.
- A rolled-back request (domain error, 4xx/5xx, failed commit) dispatches nothing.
- A failing handler is logged with the request id and does **not** change the response:
  the write is already committed and telling the client otherwise would lie. Other handlers
  still run.
- What is **not** guaranteed: delivery if the process dies between commit and dispatch,
  and retries. Delivery is at-most-once, best-effort. That is precisely the gap an outbox
  fills; until you need it, this is simpler and honest.
- Handlers must be fast and local. E-mail, third-party calls and anything retry-worthy do
  not belong in an in-process handler.
- There is no integration-event / domain-event split. Until an event leaves the process,
  the split is ceremony.

## When to revisit

Add an outbox ([recipe](../guides/extending#background-jobs--outbox)) when a handler:

- must survive the request failing after it ran (send e-mail, charge a card);
- is slow enough to hurt latency;
- lives in another process or service.

The port does not change: an outbox-backed `EventPublisher` records the same events in a
table inside the transaction, and a worker delivers them with retries.

## Proof

- proof:events-after-commit - handlers see committed state, rolled-back requests and
  failed commits dispatch nothing, a failing handler does not change the response, the CLI
  follows the same order (`tests/tournaments/test_events.py`, `tests/tournaments/test_cli.py`).
