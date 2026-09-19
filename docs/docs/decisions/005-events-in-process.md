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
- The application ring has one port, `EventPublisher.publish(events)`.
- The shipped adapter, `InProcessEventBus`, awaits every subscribed handler inside the
  request. Handlers are subscribed in `bootstrap`.
- No outbox, no broker, no background tasks.

## Consequences

- Events are testable as values: `assert result.events == (TournamentStarted(id),)`.
- Delivery is synchronous and transactional with the request: a failing handler fails the
  request and rolls back the write. Simple to reason about, no lost events.
- Handlers must be fast and local. E-mail, third-party calls and anything retry-worthy do
  not belong in an in-process handler.
- There is no integration-event / domain-event split. Until an event leaves the process,
  the split is ceremony.

## When to revisit

Add an outbox ([recipe](../guides/extending#background-jobs--outbox)) when a handler:

- must survive the request failing after it ran (send e-mail, charge a card);
- is slow enough to hurt latency;
- lives in another process or service.

The port does not change: `OutboxEventPublisher` implements the same `publish`.
