---
id: 008-persistence-model
title: "ADR-008: Separate row model, explicit mapping"
---

# ADR-008: Separate persistence model with explicit mapping

**Status:** accepted

## Context

Three ways to persist a domain object with SQLAlchemy:

1. **Make the entity the ORM model** (declarative or SQLModel). Least code; the domain now
   depends on the ORM, cannot be a frozen dataclass, and every attribute access may hit the DB.
2. **Imperative mapping onto the domain class.** Keeps the domain ORM-free on paper, but
   SQLAlchemy instruments the class (`_sa_instance_state`), which conflicts with
   `frozen=True` / `slots=True`, and nested value objects (`Phases`) need composite/JSON
   plumbing that leaks back into the domain's design.
3. **A separate row model plus a mapping module.** Most explicit; one translation to maintain.

## Decision

Option 3. `infrastructure/sqlalchemy/models.py` defines `TournamentModel(Base)`;
`mapping.py` has `to_model`, `update_model`, `to_domain`. Nested value objects are stored as a
JSON column with a documented shape. The repository is the only caller of the mapping.

## Consequences

- The domain is a plain frozen dataclass with slots, immutable and cheap.
- The table can gain indexes, denormalised columns or a soft-delete flag without touching
  the domain, and vice versa.
- One mapping to keep in sync, covered by an integration test that round-trips the whole
  aggregate through the database (`expunge_all()` guarantees a real re-read).
- The previous iteration had three copies of this mapping (domain, DTO, ORM). Now there is
  one for persistence and one for HTTP (`schemas.py`), each owned by its adapter.

## When to revisit

Phases stored as JSON cannot be queried by SQL. If you need "all tournaments with a Swiss
phase", promote phases to a child table in a migration; the mapping changes, the domain
does not.
