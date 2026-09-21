---
id: 010-optimistic-concurrency
title: "ADR-010: Optimistic concurrency on aggregates"
---

# ADR-010: Optimistic concurrency, enforced by every repository

**Status:** accepted

## Context

Two requests can load the same tournament, both call `advance()`, and both save. Without a
guard the second write silently overwrites the first: a *lost update*. We reproduced it on
SQLite with two sessions before writing this ADR. A template that promises "two
interchangeable adapters" must also promise they fail the same way.

## Decision

- Aggregates carry a `version: int` (persistence data, never touched by domain logic).
- The repository port's `save(aggregate) -> aggregate` contract: the stored version must
  equal `aggregate.version`; on success the write is applied and the returned aggregate
  carries `version + 1`; otherwise `ConflictError` is raised and **nothing is written**.
- SQLAlchemy adapter: `version_id_col` on the row model, so every update is
  `UPDATE ... WHERE id = ? AND version = ?` and a zero-row update raises `StaleDataError`,
  translated to `ConflictError`. An explicit comparison covers the case where the row was
  already reloaded in the same session. New rows start at version 0 to match the in-memory
  adapter.
- In-memory adapter: the same rule, by comparing versions.
- `ConflictError` is an `ApplicationError` → HTTP `409` with the usual envelope. The client
  reloads and retries; the CLI prints the error and exits 1.
- `tests/integration/test_tournament_repository_contract.py` runs the **same** tests against
  both adapters, including two independent readers racing on one row.

## What this does and does not guarantee

- Guaranteed: a stale write never overwrites a newer one, on every backend, without locks
  held across requests.
- Guaranteed: the conflict is observable as an application error, not as a mystery.
- Not guaranteed: a *retry* policy. Retrying is the client's decision; the template does
  not loop.
- Not guaranteed: cross-aggregate invariants. One request, one aggregate (ADR-004).

## Consequences

- Use cases return what the repository stored (`saved = await repository.save(...)`), so
  the response always reflects the persisted version.
- The `version` field is invisible to HTTP clients today. Exposing it (for example as an
  `ETag`) is a one-line change in the response schema when a client needs to send
  `If-Match`.

## Proof

- proof:optimistic-concurrency - two independent readers race on one row on both adapters;
  the second write raises `ConflictError`, exactly one version is stored, HTTP answers 409.
