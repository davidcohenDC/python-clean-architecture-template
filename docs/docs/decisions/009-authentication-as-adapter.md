---
id: 009-authentication-as-adapter
title: "ADR-009: Authentication is an adapter, authorization is a rule"
---

# ADR-009: Authentication is an adapter, authorization is an application rule

**Status:** accepted

## Context

Authentication is the most requested addition to every API template, and the place where
frameworks most easily leak inward: tokens in use cases, `request.user` in the domain,
decorators that only work under one web framework.

## Decision

Split the two concerns along the rings:

- **Authentication** (who is this?) is an HTTP adapter: `shared/http/auth.py` reads
  `X-API-Key`, looks it up in the table `bootstrap` published from `API_KEYS`, and returns
  an `Actor`. It raises `401` itself. With no keys configured it returns `ANONYMOUS`, so the
  template runs open by default.
- **`Actor`** (`shared/application/actor.py`) is the only thing that crosses the boundary: an
  id and a set of roles. No token, no header, no framework type.
- **Authorization** (may they do this?) is an application rule: `StartTournament.execute(id,
  actor)` checks `actor.id == tournament.organizer_id or actor.is_admin` and raises
  `ForbiddenError` → `403`. The domain records `organizer_id` as data and knows nothing about
  actors.
- The API-key dependency is a *real* dependency, not a placeholder overridden in `bootstrap`,
  because `dependency_overrides` do not affect the OpenAPI document and the *Authorize*
  button in Swagger would not appear.

## Consequences

- Swapping API keys for JWT, sessions or OAuth means replacing one file; use cases and tests
  that pass an `Actor` do not change.
- Authorization rules are unit-tested with fakes (`tests/application`), independently of
  HTTP; the HTTP tests only verify the mapping (`401`, `403`).
- Reads are public and writes require an actor; a stricter policy is a change in the router,
  not in the use cases.
- API keys in an environment variable are enough for a template and for internal services;
  a user-facing product needs a real identity provider - the split above is the same.

## Proof

- proof:authorization-in-application - the organizer rule is tested on use cases with fakes
  (`tests/application`), and HTTP only maps 401/403 (`tests/api/test_auth.py`).
