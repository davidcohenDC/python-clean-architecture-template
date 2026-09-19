---
id: contributing
title: Contributing & releases
sidebar_position: 9
---

# Contributing & releases

The full guide is in [`CONTRIBUTING.md`](https://github.com/davidcohenDC/python-clean-architecture-template/blob/main/CONTRIBUTING.md). The short version:

## Workflow

```bash
make install        # dependencies + git hooks (.githooks, bash)
# or, with the pre-commit framework (no Git Bash needed on Windows):
#   git config --unset core.hooksPath
#   uvx pre-commit install --hook-type pre-commit --hook-type commit-msg
git checkout -b feat/my-change
# ...
make check          # what CI runs
git commit          # commit-msg hook enforces Conventional Commits
```

## Conventional Commits

```text
feat(tournaments): allow double-elimination brackets
fix(http): map TournamentNotFound to 404
docs: explain transaction per request
refactor(shared)!: rename EventPublisher.publish to emit
```

`feat` → minor, `fix` → patch, `!` → major. `docs`, `refactor`, `test`, `ci`, `chore` do
not release on their own (`docs` and `revert` bump a patch in the preset used).

## Releases are automatic

On every push to `main`, the `release` job runs [semantic-release](https://semantic-release.gitbook.io/):

1. analyses commits since the last `vX.Y.Z` tag;
2. computes the next version;
3. writes `CHANGELOG.md`, updates `version` in `pyproject.toml` and `__version__`;
4. commits them (`chore(release): X.Y.Z [skip ci]`), tags, publishes a GitHub release;
5. `deploy-image` pushes `ghcr.io/<owner>/<repo>:X.Y.Z` and `:latest`.

To start versioning at `0.x` in a fresh fork, tag the first commit yourself:

```bash
git tag v0.1.0 && git push --tags
```

## CI layout

`.github/workflows/dispatcher.yml` decides *whether* to run (skips duplicate PR/push runs,
ignores Dependabot branches) and calls `build-and-deploy.yml`, which contains every job:

| Job | Runs on | Does |
|---|---|---|
| `code-style` | ubuntu | ruff, mypy, architecture tests |
| `test` | ubuntu / windows / macos × py3.12, 3.13 | full suite on SQLite, coverage |
| `test-postgres` | ubuntu + Postgres 17 | migrations `upgrade` + `check`, integration tests |
| `docker-build` | ubuntu | builds the image and curls `/health` |
| `dry-website-build` | ubuntu | builds the docs |
| `release` | main only | semantic-release |
| `upload-docs` | main only | publishes docs to `gh-pages` |
| `deploy-image` | main only | pushes to GHCR |
| `success` | - | single required check for branch protection |

Set `GH_TOKEN` (a PAT with `repo` scope) as a repository secret if you want release
commits to trigger further workflows; otherwise `GITHUB_TOKEN` is used.
