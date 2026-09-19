---
id: errors
title: Errors
sidebar_position: 4
---

# Errors

Three families, one per ring, and one place that maps them to HTTP.

```mermaid
flowchart LR
    DE["DomainError<br/><small>a business rule was violated</small>"] --> H
    AE["ApplicationError<br/><small>the request cannot be fulfilled</small>"] --> H
    NF["NotFoundError<br/><small>(ApplicationError)</small>"] --> H
    H["shared/http/errors.py"] --> S422["422"]
    H --> S409["409"]
    H --> S404["404"]
    style DE fill:#16a34a,color:#fff,stroke:none
    style AE fill:#2563eb,color:#fff,stroke:none
    style NF fill:#2563eb,color:#fff,stroke:none
    style H fill:#d97706,color:#fff,stroke:none
```

## Domain errors are named after the rule

```python title="tournaments/domain/errors.py"
class TournamentAlreadyStarted(DomainError):
    message = "Tournament has already started."
```

Not `TournamentError("already started")`. A specific type means:

- tests assert on the type, not on a string;
- the HTTP response carries a stable, machine-readable `error` field
  (`{"error": "TournamentAlreadyStarted", "message": "..."}`);
- the API layer can map one rule to a different status code if 422 is wrong for it,
  with `register_error(app, TournamentAlreadyStarted, 409)`.

The `...Error` suffix is deliberately *not* used for domain rules; ruff's `N818` is disabled
for that reason.

## Application errors describe the request

`TournamentNotFound(NotFoundError)` is raised by use cases, never by the domain: the domain
does not know that ids can be looked up. `ForbiddenError` (the actor may not do this) maps
to 403. Other `ApplicationError`s (a conflict, for instance) map to 409 by default.

Authentication failures are different: they happen *before* any use case runs, in the HTTP
adapter (`shared/http/auth.py`), as `HTTPException(401)`. The handler in `errors.py` wraps
them in the same envelope and keeps the `WWW-Authenticate` header.

## Nothing else crosses the boundary

- Repositories raise nothing domain-specific. A missing row is `None`; the use case turns it
  into `TournamentNotFound`.
- Infrastructure exceptions (`sqlalchemy.exc.*`, connection errors) are not translated: they
  are bugs or outages, they become a logged 500, and the transaction rolls back.
- Pydantic validation errors stay FastAPI's native 422 with a `detail` list, because clients
  and tooling already understand that format.

## Validation: shape vs rules

| Kind | Where | Example |
|---|---|---|
| Shape | Pydantic schema (`http/schemas.py`) | `rounds` must be an int; `kind` must be `round` or `bracket` |
| Rule | Domain (`__post_init__`, methods) | `rounds` must be 1-20; the first phase has no cut; can't start twice |

A rule belongs to the domain even when it is easy to express in Pydantic, because the domain
must hold on every entry path (HTTP today, a CSV import tomorrow). See
[ADR-007](../decisions/007-validation-placement).
