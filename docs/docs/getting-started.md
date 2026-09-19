---
id: getting-started
title: Getting started
sidebar_position: 2
---

# Getting started

## Prerequisites

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/) (dependency management)
- `make` (optional - every target is one command you can type by hand)
- Docker (optional - only for PostgreSQL or the container image)
- Node.js 22+ (optional - only for the documentation site and releases)

## Run it

```bash
git clone https://github.com/davidcohenDC/python-clean-architecture-template
cd python-clean-architecture-template
make install     # uv sync --all-extras && git config core.hooksPath .githooks
make run         # alembic upgrade head && uvicorn cleanarch.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs). You get a SQLite file (`dev.db`) and five endpoints
for the example feature.

No database at all? Use the in-memory adapters:

```bash
make run-memory  # DATABASE_URL=memory:// uvicorn cleanarch.main:app --reload
```

PostgreSQL:

```bash
docker compose up db -d
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app make run
```

Or the whole thing in containers: `docker compose up`.

## Try the example API

```bash
# create a tournament: 2 Swiss rounds, then a top-8 single-elimination bracket
curl -s -X POST localhost:8000/api/v1/tournaments -H 'content-type: application/json' -d '{
  "name": "Spring Cup",
  "phases": [
    {"config": {"kind": "round", "rounds": 2, "pairing": "swiss"}},
    {"config": {"kind": "bracket", "elimination": "single"}, "cut": {"players": 8}}
  ]
}'
# → 201 {"id": "...", "name": "Spring Cup", "phases": [...], "progress": {"status": "not_started", ...}}

curl -s -X POST localhost:8000/api/v1/tournaments/<id>/start     # → in_progress, phase 0, round 0
curl -s -X POST localhost:8000/api/v1/tournaments/<id>/advance   # → phase 0, round 1
curl -s -X POST localhost:8000/api/v1/tournaments/<id>/advance   # → phase 1 (bracket)
curl -s -X POST localhost:8000/api/v1/tournaments/<id>/advance   # → finished
curl -s -X POST localhost:8000/api/v1/tournaments/<id>/advance   # → 422 TournamentAlreadyFinished
```

## Run the checks

```bash
make test        # whole suite with coverage
make test-fast   # domain + application + architecture only (no I/O, < 1 s)
make lint        # ruff check + ruff format --check
make typecheck   # mypy --strict
make check       # all of the above - what CI runs
```

## Configuration

Everything is an environment variable with a default (see `.env.example` and
`bootstrap/settings.py`). Copy `.env.example` to `.env` to override locally.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./dev.db` | any SQLAlchemy async URL, or `memory://` |
| `DATABASE_ECHO` | `false` | log SQL statements |
| `LOG_LEVEL` | `INFO` | |
| `DEBUG` | `false` | FastAPI debug mode |
| `ENVIRONMENT` | `development` | `development` / `test` / `production` |

## Make it yours

```bash
uv run python scripts/init_project.py --name shopapi --remove-example
uv run python scripts/new_feature.py orders
```

See [Replace the example domain](guides/replace-example-domain).
