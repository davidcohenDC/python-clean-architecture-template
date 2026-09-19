---
id: 007-validation-placement
title: "ADR-007: Shape in Pydantic, rules in the domain"
---

# ADR-007: Validation placement

**Status:** accepted

## Context

Pydantic makes it tempting to put every rule in the request schema: `rounds: int =
Field(ge=1, le=20)`. Then the rule exists twice (schema and domain) or, worse, only in the
schema - and a second entry path (import job, CLI, another service) silently skips it.

## Decision

- **Pydantic validates shape**: types, required fields, enum membership, discriminated
  unions. It rejects malformed JSON with FastAPI's native 422.
- **The domain validates rules** in `__post_init__` and methods: ranges, invariants between
  fields, state transitions. It raises specific `DomainError`s, mapped to 422 with a stable
  `error` name.
- Schemas do **not** duplicate domain constraints, even easy ones (`min_length=1` on the
  name is deliberately absent so that a blank name reaches `InvalidTournamentName`).
- Value objects may be *constructed* in the HTTP adapter (`CreateTournamentRequest.to_command()`
  builds `Phases`), so a `DomainError` can be raised before the use case runs. That is fine:
  the rule still lives in one place, the domain, and the error mapping is the same.

## Consequences

- One source of truth per rule. A rule change is one edit and one domain test.
- Clients get two flavours of 422: Pydantic's `detail` list for shape, the error envelope
  for rules. Both are documented in OpenAPI via `responses=`.
- Some errors that Pydantic could catch at parse time are caught a few microseconds later
  by the domain. Nobody notices.

## When to revisit

If you need field-level error locations for rule violations in a form-heavy UI, have the
domain raise errors that carry a `field` attribute and extend `shared/http/errors.py` to
include it. Keep the rule in the domain.
