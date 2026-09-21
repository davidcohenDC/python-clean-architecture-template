---
id: replace-example-domain
title: Replace the example domain
sidebar_position: 2
---

# Make it your project

```bash
uv run python scripts/init_project.py --name shopapi --remove-example
```

One command, run once after cloning. It:

- renames the package (`src/shopapi/`, imports, `pyproject.toml`, `app_name`, Makefile,
  Dockerfile, docs, workflows) - pick a valid lowercase identifier;
- removes the example: `src/shopapi/tournaments/`, `bootstrap/features/tournaments.py` (and
  its entry in `FEATURES`), `tests/tournaments/`, its migrations (the chain starts empty);
- removes what only the template needs: `tests/template/` (self-checks, the proof system,
  this very journey), `proofs.toml`, `make proof`, the template README;
- writes a short README for *your* project and regenerates the dependency graph.

Then:

```bash
make check                                   # green: lint, types, architecture, tests
uv run python scripts/new_feature.py orders  # your first feature, wired and tested
make run-memory                              # POST /api/v1/orders
```

Both flags are optional. `--name` alone keeps the example under the new package name,
useful while you study it; the template-only checks are removed either way.

## What stays, and why

| Kept | Because |
|---|---|
| `shared/`, `bootstrap/` | the building blocks and the composition root: your code now |
| `scripts/archcheck.py` in `make check` and CI | the dependency rule is a durable guardrail, and a tool rather than a test so it does not dictate how you test |
| `tests/http`, `tests/bootstrap`, `tests/architecture` | the inherited mechanisms are covered without the example; delete or move them freely |
| `scripts/new_feature.py`, `scripts/graph.py` | the scaffold and the graph keep working in your project |
| `docs/` | the architecture docs and ADRs, for you to keep or replace |

## What does not stay, and why

- The example's tests and its migrations: they described a domain you do not have.
- `make proof` and `proofs.toml`: the *template's* way of proving its own claims. Your
  guarantees are your tests; the template does not impose a registry, a marker or a
  documentation contract on you.

This journey - init, green, first feature, green, served - runs as a test in the template
repository on every push (`tests/template/test_user_journey.py`).
