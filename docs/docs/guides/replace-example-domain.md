---
id: replace-example-domain
title: Replace the example domain
sidebar_position: 2
---

# Replace the example domain

The example lives in `src/cleanarch/tournaments/` plus three small blocks marked
`# >>> example: tournaments` / `# <<< example: tournaments` in `bootstrap/app.py`,
`alembic/env.py` and `tests/conftest.py`, plus its tests and one migration.

## The one-command way

```bash
uv run python scripts/init_project.py --name shopapi --remove-example
```

- `--name shopapi` renames the package everywhere (`src/shopapi/`, imports, `pyproject.toml`,
  `Makefile`, `Dockerfile`, docs, workflows). Pick a valid lowercase identifier.
- `--remove-example` deletes the tournaments feature, its tests, its migration and the marked
  blocks, then runs `ruff` to tidy up.

Then:

```bash
git diff --stat                      # review
make check                           # architecture tests still green
uv run python scripts/new_feature.py orders
```

Both flags are optional and independent. Running `--name` alone keeps the example under the
new package name, which is useful while you study it.

## The manual way

1. `rm -rf src/cleanarch/tournaments`
2. Remove the three marked blocks (`grep -rn "example: tournaments"`).
3. Delete `tests/domain/test_{phases,progress,tournament}.py`,
   `tests/application/test_use_cases.py`, `tests/integration/test_sqlalchemy_repository.py`,
   `tests/api/` contents, and `alembic/versions/20260919_0001_create_tournaments.py`.
4. `make check`.

## What stays

Everything under `shared/`, `bootstrap/`, the test layout, the tooling and the docs. That is
the template. `git log` on those paths shows they never mention tournaments.

## Keep the example around?

You can. It costs nothing at runtime, and it is a working reference for "how do I..." while
you build your first feature. Delete it when your own feature covers the same ground.
