---
id: project-structure
title: Project structure
sidebar_position: 3
---

# Project structure

`shared/` and `bootstrap/` are reused by every feature; each feature is a package of its
own. All of them follow the same four rings.
<!-- >>> example-only -->
The `tournaments` feature is the example that ships with the template: delete it with
`scripts/init_project.py --remove-example` once you have read it.
<!-- <<< example-only -->

```text
src/cleanarch/
├── shared/                        building blocks every feature reuses
│   ├── domain/        errors.py      DomainError
│   │                  events.py      DomainEvent (base)
│   │                  result.py      DomainResult[T] = new aggregate + events
│   ├── application/   errors.py      ApplicationError, NotFoundError, ForbiddenError
│   │                  actor.py       Actor, ANONYMOUS
│   │                  ports.py       EventPublisher, Clock (Protocols)
│   ├── infrastructure/database.py   engine, session factory, transaction()
│   │                  events.py      CollectedEvents (port impl), InProcessEventBus (handlers)
│   │                  clock.py       SystemClock, FixedClock
│   └── http/          errors.py      exception → HTTP status mapping
│                      auth.py        API-key authentication → Actor
│                      request_id.py  X-Request-ID middleware + ContextVar
│                      schemas.py     Schema base, ErrorResponse
│                      dependencies.py get_event_publisher, get_clock (placeholders)
│
├── tournaments/                   EXAMPLE - delete me
│   ├── domain/        tournament.py  Tournament aggregate (create/start/advance)
│   │                  phases.py      RoundPhase, BracketPhase, TopCut, Phases
│   │                  progress.py    Progress state machine
│   │                  events.py      TournamentCreated/Started/Advanced/Finished
│   │                  errors.py      TournamentAlreadyStarted, InvalidPhases, ...
│   ├── application/   ports.py       TournamentRepository (Protocol)
│   │                  commands.py    CreateTournamentCommand
│   │                  use_cases.py   CreateTournament, StartTournament, ...
│   │                  errors.py      TournamentNotFound
│   ├── infrastructure/in_memory.py  InMemoryTournamentRepository
│   │                  sqlalchemy/    models.py, mapping.py, repository.py
│   ├── http/          router.py      5 endpoints
│   │                  schemas.py     request/response models + from_domain/to_command
│   │                  dependencies.py use-case factories, get_tournament_repository
│   └── cli/           commands.py    the same use cases from the terminal
│
├── bootstrap/                     composition root
│   ├── settings.py                Settings (pydantic-settings)
│   ├── logging.py                 text or JSON logs, request id on every line
│   ├── transaction.py             TransactionMiddleware + EventDispatchMiddleware: commit, then events
│   ├── events.py                  build_event_bus(): asks every feature for its subscribers
│   ├── features/                  one module per feature: wire_http, subscribe, register_cli, run_cli
│   │   ├── __init__.py            FEATURES = [tournaments]   <- the only list to edit
│   │   └── tournaments.py         EXAMPLE
│   ├── app.py                     create_app(): middlewares, shared ports, every feature's wire_http
│   └── cli.py                     the same for the command line
├── main.py                        app = create_app()   # uvicorn cleanarch.main:app
└── __main__.py                    python -m cleanarch

tests/                         organise yours as you like; the template assumes only pytest
├── conftest.py                  client fixture, make_settings (no .env), fakes
├── http/, bootstrap/, shared/   what you inherit, tested without any feature
├── architecture/                one-line pytest wrapper around scripts/archcheck.py
├── tournaments/                 EXAMPLE - one feature tested at every level
└── template/                    TEMPLATE-ONLY - self-checks, proof system, user journey

scripts/
├── archcheck.py                 dependency rule (check) and real dependency graph (graph)
├── new_feature.py               scaffold: package + bootstrap module + first test
└── init_project.py              make it yours: rename, remove example, strip template-only

alembic/             migrations (async env, reads DATABASE_URL)
docs/                this site (Docusaurus)
.githooks/           commit-msg (Conventional Commits), pre-commit (fast checks)
.pre-commit-config.yaml  the same checks for the pre-commit framework
.github/workflows/   dispatcher.yml → build-and-deploy.yml (CI, release, docs, image)
```

## Where does X go?

| I want to add... | Put it in | Ring |
|---|---|---|
| a business rule ("a cut must be a power of two") | `<feature>/domain/` as a `__post_init__` check or a method | <span className="ring ring--domain">domain</span> |
| a new entity or value object | `<feature>/domain/<name>.py` | <span className="ring ring--domain">domain</span> |
| something that happened (`OrderShipped`) | `<feature>/domain/events.py` | <span className="ring ring--domain">domain</span> |
| a new operation ("cancel a tournament") | `<feature>/application/use_cases.py` | <span className="ring ring--application">application</span> |
| a dependency on the outside world (clock, mailer, another service) | a `Protocol` in `<feature>/application/ports.py` | <span className="ring ring--application">application</span> |
| a database table / query | `<feature>/infrastructure/sqlalchemy/` | <span className="ring ring--adapters">infrastructure</span> |
| an HTTP endpoint | `<feature>/http/router.py` + `schemas.py` | <span className="ring ring--adapters">http</span> |
| a CLI command | `<feature>/cli/commands.py` | <span className="ring ring--adapters">cli</span> |
| a new adapter implementation (Redis cache, S3 storage) | `<feature>/infrastructure/<tech>.py` | <span className="ring ring--adapters">infrastructure</span> |
| the decision of *which* adapter runs | `bootstrap/features/<feature>.py` | <span className="ring ring--bootstrap">bootstrap</span> |
| a configuration value | `bootstrap/settings.py`, passed explicitly to whoever needs it | <span className="ring ring--bootstrap">bootstrap</span> |
| code two features both need | `shared/<ring>/` - and ask yourself twice | any |

The rule of thumb: **the further out, the more replaceable.** If you could swap it for
another vendor, it is an adapter. If it would survive a rewrite of the API in another
framework, it is domain or application.
