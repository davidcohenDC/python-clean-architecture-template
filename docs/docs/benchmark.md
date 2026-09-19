---
id: benchmark
title: How it compares
sidebar_position: 8
---

# How it compares

Before settling the structure we looked at the Python repositories people actually reach
for, and at the most-starred templates in other ecosystems to see what drives adoption.
Snapshot as of September 2026.

## Python Clean Architecture / DDD repositories

| Repository | Stars | Strong | Weak | Kept / avoided here |
|---|---|---|---|---|
| [cosmicpython/code](https://github.com/cosmicpython/code) | 2.7k | Repository, UoW, message bus explained by a book; tests split by level | Flask, sync, Python 3.8, no typing | kept the test split; avoided the service-layer-without-ports shape |
| [pgorecki/python-ddd](https://github.com/pgorecki/python-ddd) | 1k | event storming, context maps, blog | a DDD project, not a template; WIP | avoided multi-context scope |
| [iktakahiro/dddpy](https://github.com/iktakahiro/dddpy) | 730 | didactic README with curl; frozen value objects; `Depends` as DI | TODO domain too thin; no events; no architecture tests | kept `Depends`-only DI and curl examples |
| [ivan-borovets/fastapi-clean-example](https://github.com/ivan-borovets/fastapi-clean-example) | 589 | no globals, UoW done right, uv/ruff/mypy/Alembic | README "refactor in progress", incomplete tests | kept the tooling bar; avoided CQRS + RBAC + sessions in a template |
| [0xTheProDev/fastapi-clean-example](https://github.com/0xTheProDev/fastapi-clean-example) | 510 | REST + GraphQL | `models/crud/services` layering, not Clean Architecture; unmaintained | - |
| [qu3vipon/python-ddd](https://github.com/qu3vipon/python-ddd) | 456 | imperative SQLAlchemy mapping | no tests; heavy DI library | avoided `dependency-injector` |
| [lgiordani/rentomatic](https://github.com/lgiordani/rentomatic) | 421 | free book "Clean Architectures in Python" | 2018-era tooling | - |
| [BrunoTanabe/fastapi-clean-architecture-ddd-template](https://github.com/BrunoTanabe/fastapi-clean-architecture-ddd-template) | 23 | feature-first modules with four rings; module scaffold script; step-by-step "replace the domain" | pytest not even a dependency; nine modules + JWT + Redis | kept feature-first + scaffold; avoided the scope |
| [bodaue/fastapi-clean-architecture](https://github.com/bodaue/fastapi-clean-architecture) | 31 | `main/` as composition root | Dishka + Poetry, no tests | kept an explicit composition root |

Common gap: none of those we reviewed combine executable boundary tests (import-linter
exists and some projects use it, but rarely with the rest), a realistic-but-small domain, a
navigable explanation of the request flow, a verified domain-replacement procedure and all
five test levels. The most-starred are books or "refactor in progress".

## What the most-starred templates elsewhere teach

| Template | Stars | Lesson applied |
|---|---|---|
| [jasontaylordev/CleanArchitecture](https://github.com/jasontaylordev/CleanArchitecture) (.NET) | 20k | badges + 3-command start at the top; "architectural decisions" section; multi-DB via option |
| [ardalis/CleanArchitecture](https://github.com/ardalis/CleanArchitecture) (.NET) | 18k | *Design decisions and dependencies* explained, e.g. where validation goes → our ADRs |
| [bulletproof-react](https://github.com/alan2207/bulletproof-react) | 36k | docs-first; "not a framework"; principles stated up-front; sample app separate from guidelines |
| [create-t3-app](https://github.com/t3-oss/create-t3-app) | 29k | opinionated but modular: each piece optional → recipes instead of baked-in features |
| [cookiecutter-django](https://github.com/cookiecutter/cookiecutter-django) | 14k | project rename on init; 100 % starting coverage; Dependabot → `init_project.py` |
| [brocoders/nestjs-boilerplate](https://github.com/brocoders/nestjs-boilerplate) | 4k | resource generator; DB chosen by env → `new_feature.py`, `DATABASE_URL` |
| [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | 46k | the DX bar: uv, compose, CI, "Use this template" (its layering is flat by design) |

What we saw fail: READMEs that say "docs coming", patterns present but unexplained, empty
test scaffolds, and templates whose understanding depends on a paid course.

## Why choose this one

> Boundaries verified by tests that run in CI, an example domain removed with one command,
> and a written reason for every pattern present - or absent. We have not found another
> Python template that does all three; if you know one, open an issue and we will link it.
