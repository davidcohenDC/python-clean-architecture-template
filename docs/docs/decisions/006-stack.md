---
id: 006-stack
title: "ADR-006: The stack"
---

# ADR-006: FastAPI, SQLAlchemy 2 async, Alembic, uv, Ruff, mypy

**Status:** accepted

## Context

A template's stack is judged twice: is it what people expect in 2026, and does it stay out
of the inner rings?

## Decision

| Concern | Choice | Why | Why not the alternatives |
|---|---|---|---|
| HTTP | **FastAPI** | de-facto standard for typed async Python APIs; `Depends` is enough DI; OpenAPI for free | Litestar is excellent but smaller; Django REST couples the ORM to everything |
| Validation at the edge | **Pydantic v2** | comes with FastAPI; fast; `extra="forbid"` catches client typos | used *only* in `http/` and `bootstrap/settings.py` |
| Persistence | **SQLAlchemy 2.0 async** + separate row models | mature, typed `Mapped[]`, any SQL database; the domain stays framework-free | SQLModel merges Pydantic + table into the entity - exactly the coupling we avoid; raw asyncpg means writing an ORM |
| Migrations | **Alembic** | the SQLAlchemy migration tool; `render_as_batch` covers SQLite | - |
| Default DB | **SQLite** (`aiosqlite`) | zero setup; the point is to run in two minutes | PostgreSQL is one env var and a compose file away, and CI tests it |
| Package manager | **uv** | fast, lockfile, single tool for venv + deps + running | Poetry works; uv has become the default for new projects |
| Lint + format | **Ruff** | replaces black, isort, flake8, pyupgrade with one config | - |
| Types | **mypy --strict** | Protocol conformance is what makes ports safe | pyright is a fine swap; strictness is the point |
| Tests | **pytest** + `pytest-asyncio` (auto mode) + `httpx` | - | - |
| Settings | **pydantic-settings** | typed env parsing; lives in `bootstrap` only | - |
| Docs | **Docusaurus** + Mermaid | navigable site, diagrams in Markdown, GitHub Pages | MkDocs Material is a good alternative |
| CI | **GitHub Actions**, reusable workflow, semantic-release | Conventional Commits drive versions, changelog, tags, GHCR image | - |

## Consequences

- Inner rings import nothing but the standard library; the architecture tests pin this.
- Everything above is replaceable from the outside in: HTTP framework in `http/` +
  `bootstrap/`, ORM in `infrastructure/` + `shared/infrastructure/`, tooling in `pyproject.toml`.
- Python 3.12+ is required (PEP 695 generics, `StrEnum`, `Self`).

## Proof

No executable proof: a technology choice. What the inner rings may import is covered by
proof:dependency-rule, not by this decision.
