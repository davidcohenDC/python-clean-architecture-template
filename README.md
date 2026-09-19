# Python Clean Architecture Template

[![CI/CD](https://github.com/davidcohenDC/python-clean-architecture-template/actions/workflows/dispatcher.yml/badge.svg)](https://github.com/davidcohenDC/python-clean-architecture-template/actions/workflows/dispatcher.yml)
[![codecov](https://codecov.io/gh/davidcohenDC/python-clean-architecture-template/branch/main/graph/badge.svg)](https://codecov.io/gh/davidcohenDC/python-clean-architecture-template)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-fe5196.svg)](https://conventionalcommits.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A working starter kit, a reference implementation and a practical guide to Clean
Architecture in modern Python - in one repository.**

FastAPI · SQLAlchemy 2 async · Alembic · uv · Ruff · mypy strict · pytest ·
executable architecture tests · Docker · GitHub Actions · semantic-release · Docusaurus docs

📖 **[Documentation](https://davidcohendc.github.io/python-clean-architecture-template/)** ·
[Architecture](https://davidcohendc.github.io/python-clean-architecture-template/architecture/overview) ·
[Decisions (ADR)](https://davidcohendc.github.io/python-clean-architecture-template/decisions) ·
[Replace the example domain](https://davidcohendc.github.io/python-clean-architecture-template/guides/replace-example-domain)

---

## Why this template

Most "clean architecture" repositories have the folders but not the boundaries: the domain
imports the ORM, use cases pull dependencies from a global container, and nothing stops the
next commit from making it worse. Others have every pattern from the book and no explanation
of which ones the problem actually needed.

This one is different in three verifiable ways:

1. **The boundaries are tests.** `tests/architecture` parses every module and fails the build
   if a dependency points outward or a framework leaks into `domain`/`application`.
   It runs in the pre-commit hook and in CI.
2. **Every pattern has a written reason - including the absent ones.** Eight ADRs explain
   why there is no DI container, no mediator, no Unit of Work, no outbox, and exactly when
   you should add each.
3. **The example is removed with one command.** `shared/` + `bootstrap/` are the template;
   `tournaments/` is the example. `scripts/init_project.py --remove-example` deletes it,
   `scripts/new_feature.py` scaffolds yours with all four rings wired.

```text
git clone / use template → make install → make run → open /docs
   → read one feature → understand the architecture → replace the example → build
```

## Quick start

```bash
git clone https://github.com/davidcohenDC/python-clean-architecture-template
cd python-clean-architecture-template
make install        # uv sync + git hooks
make run            # migrations + uvicorn with reload → http://localhost:8000/docs
```

No database? `make run-memory`. PostgreSQL? `docker compose up`. Everything CI runs: `make check`.

<details>
<summary>Without <code>make</code></summary>

```bash
uv sync --all-extras
git config core.hooksPath .githooks
uv run alembic upgrade head
uv run uvicorn cleanarch.main:app --reload
```
</details>

## The architecture in one picture

```mermaid
flowchart TB
    subgraph B["bootstrap · composition root: knows every concrete class"]
        subgraph A["adapters · infrastructure (SQLAlchemy, in-memory, event bus) | http (FastAPI)"]
            subgraph AP["application · use cases + ports (Protocols)"]
                D["domain · entities, value objects, events, rules · stdlib only"]
            end
        end
    end
    style D fill:#16a34a,color:#fff,stroke:none
    style AP fill:#2563eb,color:#fff,stroke:none
    style A fill:#d97706,color:#fff,stroke:none
    style B fill:#6b7280,color:#fff,stroke:none
```

**Dependencies point inward, always.** `infrastructure` and `http` sit on the same ring and
never import each other; they meet only in `bootstrap`.

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant R as http/router.py
    participant U as application/use_cases.py
    participant T as domain/tournament.py
    participant P as infrastructure/sqlalchemy
    participant E as InProcessEventBus
    C->>R: POST /tournaments/{id}/start
    R->>U: StartTournament.execute(id)   (built by Depends, ports overridden in bootstrap)
    U->>P: repository.get(id)
    P-->>U: Tournament
    U->>T: tournament.start()
    T-->>U: DomainResult(new Tournament, (TournamentStarted,))
    U->>P: repository.save(new)
    U->>E: publish(events)
    U-->>R: Tournament
    R-->>C: 200 TournamentResponse.from_domain(...)
    Note over P: TransactionMiddleware commits before the response is sent
```

## Project layout

```text
src/cleanarch/
├── shared/           TEMPLATE  building blocks: DomainEvent, DomainResult, errors,
│                               EventPublisher port, DB session, in-process bus, HTTP error mapping
├── tournaments/      EXAMPLE   one feature, four rings:
│   ├── domain/                 Tournament aggregate, phases, progress, events, rules
│   ├── application/            use cases, TournamentRepository port, command
│   ├── infrastructure/         in_memory.py · sqlalchemy/{models,mapping,repository}.py
│   └── http/                   router, schemas, use-case factories
├── bootstrap/        TEMPLATE  settings.py · app.py (wires ports → adapters, mounts routers)
└── main.py                     uvicorn cleanarch.main:app

tests/
├── domain/           pure rules, no I/O                          ms
├── application/      use cases with the in-memory adapter        ms
├── integration/      SQLAlchemy adapter on SQLite / PostgreSQL   ~100 ms
├── api/              HTTP boundary, error envelope               ms
└── architecture/     the Dependency Rule, executable             ms
```

## The example feature

A tournament is a sequence of phases (Swiss/round-robin rounds, single/double elimination
brackets), each after the first preceded by a top-N cut. It can be created, started and
advanced round by round until it finishes. Real invariants, real state machine, real events -
readable in five minutes.

<details>
<summary>Glossary, if you don't play tournaments</summary>

- **Swiss / round-robin** - pairing systems for round-based phases: everybody plays a fixed number of rounds.
- **Bracket** - knock-out phase: single elimination (lose once, out) or double.
- **Cut** - who advances into a later phase, e.g. *top 8*. The first phase has no cut; every later phase needs one.
- **Progress** - where the tournament is: not started, phase *i* / round *j*, or finished.
</details>

```bash
curl -s -X POST localhost:8000/api/v1/tournaments -H 'content-type: application/json' -d '{
  "name": "Spring Cup",
  "phases": [
    {"config": {"kind": "round", "rounds": 2, "pairing": "swiss"}},
    {"config": {"kind": "bracket", "elimination": "single"}, "cut": {"players": 8}}
  ]}'
curl -s -X POST localhost:8000/api/v1/tournaments/<id>/start
curl -s -X POST localhost:8000/api/v1/tournaments/<id>/advance
curl -s -X POST localhost:8000/api/v1/tournaments/<id>/start
# → 422 {"error": "TournamentAlreadyStarted", "message": "Tournament has already started."}
```

The whole use case:

```python
class StartTournament:
    def __init__(self, repository: TournamentRepository, events: EventPublisher) -> None:
        self._repository = repository
        self._events = events

    async def execute(self, tournament_id: TournamentId) -> Tournament:
        tournament = await _require(self._repository, tournament_id)
        result = tournament.start()  # DomainResult: new aggregate + events
        await self._repository.save(result.aggregate)
        await self._events.publish(result.events)
        return result.aggregate
```

## Make it yours

```bash
uv run python scripts/init_project.py --name shopapi --remove-example   # rename + drop the example
uv run python scripts/new_feature.py orders                             # scaffold a feature
make check                                                              # still green
```

`new_feature.py` generates a working vertical slice - entity, event, repository port, two use
cases, in-memory adapter, router - that already passes the architecture tests. Wire two
lines in `bootstrap/app.py` and `POST /api/v1/orders` works.

## Design decisions

| Decision | Why | Add it when... | ADR |
|---|---|---|---|
| Feature-first layout, rings inside | delete a feature = delete a folder; rings still enforced per feature | - | [001](docs/docs/decisions/001-feature-first-layout.md) |
| No DI library | `Depends` + `dependency_overrides` in one composition root; nothing to learn | the object graph gets deep | [002](docs/docs/decisions/002-no-di-library.md) |
| No mediator / CQRS bus | use cases are classes you call; greppable | several entrypoints need one pipeline | [003](docs/docs/decisions/003-no-mediator-no-cqrs.md) |
| Transaction per request, no UoW | session opened/committed by the HTTP layer; use cases stay 4 lines | two aggregates per operation, or non-HTTP entrypoints | [004](docs/docs/decisions/004-transaction-per-request.md) |
| Events in-process | values returned by domain methods, awaited in the request | a handler must outlive the request (e-mail, broker) | [005](docs/docs/decisions/005-events-in-process.md) |
| FastAPI + SQLAlchemy 2 + Alembic + uv + Ruff + mypy | mainstream, typed, confined to the outer rings | - | [006](docs/docs/decisions/006-stack.md) |
| Shape in Pydantic, rules in the domain | one source of truth per rule, on every entry path | - | [007](docs/docs/decisions/007-validation-placement.md) |
| Separate row model + explicit mapping | frozen dataclass domain; table evolves independently | - | [008](docs/docs/decisions/008-persistence-model.md) |

## Tooling

| | |
|---|---|
| `make test` / `make test-fast` | full suite with coverage / domain + application + architecture only |
| `make lint` / `make format` / `make typecheck` | Ruff, Ruff --fix, mypy --strict |
| `make migrate` / `make migration m="..."` | Alembic upgrade / autogenerate |
| `make docs` | Docusaurus dev server |
| `docker compose up` | API + PostgreSQL 17 |
| `.githooks/` | `commit-msg` enforces Conventional Commits; `pre-commit` runs the fast checks |
| `.github/workflows/` | lint · tests on 3 OS × 2 Pythons · Postgres integration · Docker smoke test · docs · semantic-release · GHCR image |

Releases are automatic: Conventional Commits on `main` → version, `CHANGELOG.md`, tag, GitHub
release and `ghcr.io/<owner>/<repo>:X.Y.Z`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## How it compares

We benchmarked the popular Python Clean Architecture / DDD repositories and the most-starred
templates in other ecosystems before settling the structure. The short version is in the
[docs](https://davidcohendc.github.io/python-clean-architecture-template/benchmark); the one-line
version:

> Boundaries verified by tests that run in CI, an example domain removed with one command,
> and a written reason for every pattern present - or absent. We have not found another
> Python template that does all three; if you know one, open an issue and we will link it.

## Contributing

Issues and PRs are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first - the bar is
"does it make the architecture clearer for the next person who forks it?".

## License

[MIT](LICENSE). Free to use, fork and ship. If it saved you time, a star helps others find it.
