---
id: intro
title: What this is
slug: /
sidebar_position: 1
---

# Python Clean Architecture Template

A **working starter kit**, a **reference implementation** and a **practical guide** to
Clean Architecture in modern Python - in one repository.

```text
git clone / use template  →  make install  →  make run  →  open /docs
        →  read one feature  →  understand the architecture
        →  replace the example domain  →  start building
```

## Why it exists

Most "clean architecture" repositories fall into one of two traps:

- **Folders, not boundaries.** `domain/`, `application/`, `infrastructure/` exist, but the domain
  imports the ORM, use cases resolve dependencies from a global container, and nothing stops the
  next commit from making it worse.
- **Patterns, not reasons.** Mediators, CQRS, unit of work, DI containers, outboxes - all present,
  none explained, most unnecessary for the problem at hand.

This template takes the opposite stance:

| Principle | How it shows up |
|---|---|
| **Boundaries are executable** | `tests/architecture` parses every module and fails the build if a dependency points outward or a framework leaks into `domain`/`application`. |
| **Every pattern has a reason** | Each decision has an ADR. Patterns we deliberately *left out* (DI container, mediator, UoW, outbox) have one too, with the moment you would add them. |
| **Template and example are separated** | `shared/` and `bootstrap/` are the template. `tournaments/` is the example. `scripts/init_project.py --remove-example` deletes it; `scripts/new_feature.py` scaffolds yours. |
| **Realistic but small example** | A tournament with phases, cuts and a start/advance state machine: real invariants, real events, still readable in five minutes. |
| **Zero-friction start** | SQLite by default, `DATABASE_URL=memory://` for no database at all, PostgreSQL via `docker compose`. |

## Who it is for

- Developers who want to **start an API today** on a structure that will still make sense in a year.
- Teams who want a **shared reference** for "where does this code go?".
- Anyone who has read about Clean Architecture and wants to **see it applied**, including
  the parts where the book's diagrams meet Python's pragmatism.

## What it is not

- Not a framework. There is nothing to learn beyond FastAPI, SQLAlchemy and plain Python.
- Not a DDD showcase. Tactical DDD concepts (aggregate, value object, domain event) appear
  only where the example domain genuinely benefits from them.
- Not feature-complete. Authentication, caching, background jobs are *recipes* in
  [Extending](guides/extending), not baked in.

## Next

- [Getting started](getting-started) - running in two minutes.
- [Architecture overview](architecture/overview) - the four rings and the Dependency Rule.
- [Replace the example domain](guides/replace-example-domain) - make it yours.
