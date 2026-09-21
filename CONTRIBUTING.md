# Contributing

Thanks for helping. This project is a *template*, so contributions are judged on one question:
**does it make the architecture clearer for the next person who forks it?**

## Setup

```bash
git clone https://github.com/davidcohenDC/python-clean-architecture-template
cd python-clean-architecture-template
make install      # uv sync + git hooks (.githooks)
make check        # lint, types, tests: everything CI runs
```

## What we welcome

- Bug fixes and clearer error messages.
- Documentation that explains a *why*, or fixes something misleading.
- Recipes in `docs/docs/guides/extending.md` (auth, outbox, another database…) that stay **optional**.
- Tooling that removes friction without adding files people have to understand.

## What we push back on

- New patterns without a problem they solve *in this template* (see the ADRs in `docs/docs/decisions/`).
- Anything that leaks a framework into `domain/` or `application/` — `tests/architecture` will fail anyway.
- Growing the example domain. `tournaments` must stay understandable in five minutes.
- Libraries a fork would have to learn before understanding the architecture (DI containers, mediators, ORMs that shape the domain).

## Commits and releases

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/); the
`commit-msg` hook rejects anything else. Two equivalent hook setups exist - pick one:

- `make install` → bash hooks in `.githooks/` (needs Git Bash on Windows);
- `uvx pre-commit install --hook-type pre-commit --hook-type commit-msg` → the
  [pre-commit](https://pre-commit.com) framework with `.pre-commit-config.yaml` (run
  `git config --unset core.hooksPath` first if you used `make install`). Types: `feat`, `fix`, `docs`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`, `style`, `revert`. Add `!` for a breaking change.

Releases are automatic: on every push to `main`, semantic-release reads the commits since
the last tag, bumps the version (`feat` → minor, `fix` → patch, `!` → major), updates
`CHANGELOG.md`, `pyproject.toml` and `__version__`, tags `vX.Y.Z`, publishes a GitHub
release and pushes the Docker image to GHCR. You never edit the version by hand.

## Architectural guarantees

If your change touches a property listed in `proofs.toml`, keep its evidence green
(`make proof`) and its ADR's `## Proof` section true. A new guarantee needs a test marked
`@pytest.mark.proof("<id>")`, a registry entry, the ADR reference and a README row - the
registry check tells you what is missing. Do not add a guarantee without a test that would
fail if it were false.

## Pull requests

1. Open an issue first for anything bigger than a small fix, so we can agree on the approach.
2. Keep PRs focused. One idea per PR.
3. `make check` must pass. CI runs the same commands.
4. If you change a decision, add or amend an ADR in `docs/docs/decisions/` in the same PR.
5. Fill in the PR template.

## Style

Ruff decides formatting and import order; mypy runs in strict mode; the architecture tests decide what may import what.
If a rule feels wrong, open an issue — the rules are meant to be *explained*, not just enforced.
