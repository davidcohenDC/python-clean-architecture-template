---
id: index
title: Architecture decisions
slug: /decisions
---

# Architecture decision records

Every non-obvious choice in the template has a record: the context, the decision, the
consequences, and - for patterns we left out - the condition under which you should add them.

| # | Decision | One line |
|---|---|---|
| [001](./001-feature-first-layout.md) | Feature-first layout, rings inside | Delete a feature = delete a folder; rings still enforced |
| [002](./002-no-di-library.md) | No DI library | FastAPI `Depends` + explicit overrides in `bootstrap` |
| [003](./003-no-mediator-no-cqrs.md) | No mediator, no CQRS bus | Use cases are classes you call; read models when queries hurt |
| [004](./004-transaction-per-request.md) | Transaction per request, no Unit of Work | Session opened/committed by the HTTP layer |
| [005](./005-events-in-process.md) | Domain events dispatched in-process | Outbox + broker only when a handler can't be awaited |
| [006](./006-stack.md) | FastAPI, SQLAlchemy 2 async, Alembic, uv, Ruff, mypy | Mainstream, typed, replaceable at the edges |
| [007](./007-validation-placement.md) | Shape in Pydantic, rules in the domain | The domain must hold on every entry path |
| [008](./008-persistence-model.md) | Separate row model + explicit mapping | Frozen dataclass domain, table free to evolve |
| [009](./009-authentication-as-adapter.md) | Authentication is an adapter, authorization a rule | API key → `Actor`; use cases decide, domain records `organizer_id` |

Format: [Michael Nygard's ADR](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
Add a new one with the next number when you change a decision in your fork; keep the old
one and mark it *superseded*.
