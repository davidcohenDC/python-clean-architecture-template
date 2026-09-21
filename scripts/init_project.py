#!/usr/bin/env python
"""Turn the template into *your* project. Run it once, right after cloning.

    uv run python scripts/init_project.py --name shopapi --remove-example

* ``--name``            renames the Python package (``cleanarch`` -> ``shopapi``)
                        everywhere: source, tests, alembic, Docker, Makefile, docs.
* ``--remove-example``  deletes the ``tournaments`` feature (its package, its
                        bootstrap module, its tests, its migrations).

Whatever the flags, it also removes what only makes sense in the template
repository (its self-tests, the proof registry, the template README, links
to the template's own GitHub project) and writes a README, a CONTRIBUTING and
docs metadata for the new project. The result is green on ``make check`` and
ready for ``scripts/new_feature.py``.

Safe to run on a clean git tree; review with ``git diff``.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT_PACKAGE = "cleanarch"
EXAMPLE = "tournaments"
TEMPLATE_REPO = "davidcohenDC/python-clean-architecture-template"

TEXT_GLOBS = [
    "pyproject.toml",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "alembic.ini",
    "README.md",
    "CONTRIBUTING.md",
    "release.config.mjs",
    "alembic/**/*.py",
    "src/**/*.py",
    "tests/**/*.py",
    "scripts/**/*.py",
    "docs/docs/**/*.md",
    "docs/docs/**/*.mdx",
    ".github/**/*.yml",
    ".github/**/*.md",
    ".githooks/*",
    ".pre-commit-config.yaml",
]

# Only meaningful in the template repository itself.
TEMPLATE_ONLY = [
    "tests/template",
    "proofs.toml",
    "scripts/proof.py",
    "docs/docs/proofs.md",
    "docs/docs/benchmark.md",
    "docs/docs/contributing.md",
    "docs/docs/guides/replace-example-domain.md",
    ".github/FUNDING.yml",
]
SIDEBAR_ENTRIES = ("proofs", "benchmark", "contributing", "guides/replace-example-domain")

# The example feature: one package, one bootstrap module, one test folder, its migrations.
EXAMPLE_PATHS = [
    "src/{pkg}/" + EXAMPLE,
    "src/{pkg}/bootstrap/features/" + EXAMPLE + ".py",
    "tests/" + EXAMPLE,
]
EXAMPLE_MIGRATIONS = "alembic/versions"


def block(tag: str) -> re.Pattern[str]:
    """``# >>> <tag>`` ... ``# <<< <tag>`` (or ``<!-- -->``), the marked lines included."""
    return re.compile(
        rf"^[ \t]*(#|<!--)[ ]*>>> {tag}.*?^[ \t]*(#|<!--)[ ]*<<< {tag}[^\n]*\n",
        re.DOTALL | re.MULTILINE,
    )


TEMPLATE_BLOCK = block("template-only")
EXAMPLE_BLOCK = block("example-only")
# ADRs end with a ``## Proof`` section pointing at the template's proof registry.
PROOF_SECTION = re.compile(r"\n## Proof\n.*\Z", re.DOTALL)
# Directory trees in the docs: a ``├──`` entry that became the last of its group.
LAST_TREE_ENTRY = re.compile(r"^((?:│   )*)├──(.*)\n(?!\1[│├└])", re.M)
# ``@pytest.mark.proof(...)``: evidence for the template's registry, gone with it.
PROOF_DECORATOR = re.compile(r"^[ \t]*@pytest\.mark\.proof\(.*\)\n", re.M)
PROOF_MODULE_MARK = re.compile(r"^pytestmark = pytest\.mark\.proof\(.*\)\n\n?", re.M)
PROOF_LIST_ENTRY = re.compile(r"pytest\.mark\.proof\([^)]*\),?\s*")
EMPTY_MARK_LIST = re.compile(r"^pytestmark = \[\s*\]\n\n?", re.M)


def text_files() -> list[Path]:
    files: list[Path] = []
    for pattern in TEXT_GLOBS:
        files.extend(p for p in ROOT.glob(pattern) if p.is_file())
    return files


def remove(relative: str) -> None:
    path = ROOT / relative
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def edit(path: Path, *rules: tuple[str | re.Pattern[str], str]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for pattern, replacement in rules:
        if isinstance(pattern, str):
            text = text.replace(pattern, replacement)
        else:
            text = pattern.sub(replacement, text)
    path.write_text(text, encoding="utf-8")


def rename_package(new: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", new):
        sys.exit("package name must be a valid lowercase Python identifier")
    src_old, src_new = ROOT / "src" / CURRENT_PACKAGE, ROOT / "src" / new
    if src_new.exists():
        sys.exit(f"{src_new} already exists")
    for path in text_files():
        content = path.read_text(encoding="utf-8")
        updated = re.sub(rf"\b{CURRENT_PACKAGE}\b", new, content)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
    src_old.rename(src_new)
    edit(
        ROOT / "pyproject.toml", ('name = "python-clean-architecture-template"', f'name = "{new}"')
    )
    edit(
        ROOT / "src" / new / "bootstrap" / "settings.py",
        ('app_name: str = "python-clean-architecture-template"', f'app_name: str = "{new}"'),
    )
    print(f"renamed package {CURRENT_PACKAGE} -> {new}")


def strip_proof_markers(source: str) -> str:
    source = PROOF_DECORATOR.sub("", source)
    source = PROOF_MODULE_MARK.sub("", source)
    source = PROOF_LIST_ENTRY.sub("", source)
    return EMPTY_MARK_LIST.sub("", source)


def strip_template_only() -> None:
    for relative in TEMPLATE_ONLY:
        remove(relative)
    for path in text_files():
        content = path.read_text(encoding="utf-8")
        updated = TEMPLATE_BLOCK.sub("", content)
        if path.suffix == ".py" and "tests" in path.parts:
            updated = strip_proof_markers(updated)
        if "decisions" in path.parts:
            updated = PROOF_SECTION.sub("\n", updated)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
    edit(ROOT / "pyproject.toml", (re.compile(r'^\s*"proof\(\*ids\).*\n', re.M), ""))
    edit(
        ROOT / "docs" / "docs" / "project-structure.md",
        (re.compile(r"^.*TEMPLATE-ONLY.*\n", re.M), ""),
        (re.compile(r"^.*init_project\.py .*\n", re.M), ""),
        (LAST_TREE_ENTRY, r"\1└──\2\n"),
    )
    (ROOT / "CHANGELOG.md").write_text(
        "# Changelog\n\nWritten by semantic-release from Conventional Commits.\n",
        encoding="utf-8",
    )
    print("removed the template's own checks (tests/template, proofs.toml, make proof)")


def remove_example(pkg: str) -> None:
    for relative in EXAMPLE_PATHS:
        remove(relative.format(pkg=pkg))
    for migration in (ROOT / EXAMPLE_MIGRATIONS).glob("*.py"):
        migration.unlink()  # every shipped migration belongs to the example
    init = ROOT / "src" / pkg / "bootstrap" / "features" / "__init__.py"
    text = init.read_text(encoding="utf-8")
    text = re.sub(rf"^from {pkg}\.bootstrap\.features import {EXAMPLE}\n", "", text, flags=re.M)
    text = re.sub(rf"(?<=[\[, ]){EXAMPLE}\b,?\s*", "", text)  # drop it from the FEATURES list
    text = text.replace("import ,", "import").replace("[, ", "[")
    text = re.sub(r"^from \S+ import\s*$\n?", "", text, flags=re.M)  # an emptied import line
    init.write_text(text, encoding="utf-8")
    for path in text_files():
        content = path.read_text(encoding="utf-8")
        updated = EXAMPLE_BLOCK.sub("", content)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
    edit(  # the directory tree of the docs
        ROOT / "docs" / "docs" / "project-structure.md",
        (re.compile(rf"^├── {EXAMPLE}/ .*?\n│\n", re.M | re.DOTALL), ""),
        (re.compile(rf"^.*(?:/|\b){EXAMPLE}(?:\.py|/)? +EXAMPLE.*\n", re.M), ""),
        (f"FEATURES = [{EXAMPLE}]", "FEATURES = [...]"),
        (LAST_TREE_ENTRY, r"\1└──\2\n"),
    )
    print(f"removed the {EXAMPLE} example (package, bootstrap module, tests, migrations)")


def github_repo() -> str | None:
    """``owner/name`` of the ``origin`` remote when it is on GitHub, else ``None``."""
    try:
        url = subprocess.run(
            ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def rebrand(pkg: str) -> None:
    """Metadata, docs site and contributor files stop pointing at the template."""
    repo = github_repo()
    owner, name = repo.split("/") if repo else ("your-github-user", pkg)
    edit(
        ROOT / "pyproject.toml",
        (re.compile(r'^description = ".*"$', re.M), f'description = "{pkg} API"'),
        (re.compile(r"^keywords = \[.*\]$", re.M), "keywords = []"),
        (re.compile(r"^\[project\.urls\]\n(?:.+\n)+", re.M), ""),
    )
    edit(
        ROOT / "package.json",
        (re.compile(r'"name": ".*?"'), f'"name": "{name}"'),
        (re.compile(r'"url": ".*?"'), f'"url": "https://github.com/{owner}/{name}/issues"'),
        (re.compile(r'"homepage": ".*?"'), f'"homepage": "https://github.com/{owner}/{name}"'),
    )
    edit(
        ROOT / "package-lock.json",
        ('"name": "python-clean-architecture-template"', f'"name": "{name}"'),
    )
    edit(ROOT / ".env.example", (re.compile(r"^APP_NAME=.*$", re.M), f"APP_NAME={pkg}"))
    # The template's version history is not yours: semantic-release starts over from the tags.
    edit(ROOT / "pyproject.toml", (re.compile(r'^version = ".*"$', re.M), 'version = "0.0.0"'))
    edit(
        ROOT / "src" / pkg / "__init__.py",
        (re.compile(r'^__version__ = ".*"$', re.M), '__version__ = "0.0.0"'),
    )
    edit(
        ROOT / "src" / pkg / "__init__.py", ('"""python-clean-architecture-template.', f'"""{pkg}.')
    )
    edit(
        ROOT / "docs" / "docusaurus.config.ts",
        (re.compile(r'const organization = ".*";'), f'const organization = "{owner}";'),
        (re.compile(r'const project = ".*";'), f'const project = "{name}";'),
        (re.compile(r'const pagesHost = ".*";'), f'const pagesHost = "{owner.lower()}.github.io";'),
        ('title: "Python Clean Architecture Template"', f'title: "{pkg}"'),
        ('title: "Clean Architecture Template"', f'title: "{pkg}"'),
        (re.compile(r'tagline: ".*"'), f'tagline: "{pkg} - architecture handbook"'),
    )
    gone = "|".join(re.escape(entry) for entry in SIDEBAR_ENTRIES)
    edit(ROOT / "docs" / "sidebars.ts", (re.compile(rf'^\s*"({gone})",\n', re.M), ""))
    edit(
        ROOT / "docs" / "docs" / "getting-started.md",
        (
            re.compile(r"^git clone .*\ncd .*$", re.M),
            f"git clone git@github.com:{owner}/{name}.git\ncd {name}",
        ),
        (re.compile(r"^make proof .*\n", re.M), ""),
    )
    intro = ROOT / "docs" / "docs" / "intro.md"
    if intro.exists():
        intro.write_text(INTRO.format(pkg=pkg, template=TEMPLATE_REPO), encoding="utf-8")
    (ROOT / "CONTRIBUTING.md").write_text(
        CONTRIBUTING.format(pkg=pkg, template=TEMPLATE_REPO), encoding="utf-8"
    )


def write_readme(pkg: str) -> None:
    (ROOT / "README.md").write_text(
        README.format(pkg=pkg, template=TEMPLATE_REPO), encoding="utf-8"
    )


INTRO = """---
id: intro
title: Architecture handbook
slug: /
sidebar_position: 1
---

# {pkg}: architecture handbook

This project follows Clean Architecture as laid out by
[python-clean-architecture-template](https://github.com/{template}): features made of four
rings (`domain` -> `application` -> `infrastructure` | `http` | `cli`), dependencies pointing
inward and checked by `scripts/archcheck.py`, a composition root in `bootstrap/`.

- [Getting started](getting-started) - run it, run the checks.
- [Architecture](architecture/overview) - the rings, the request flow, ports and adapters.
- [Guides](guides/add-a-feature) - add a feature, change the database, extend.
- [Decisions](decisions) - why things are the way they are.
"""

CONTRIBUTING = """# Contributing

```bash
make install      # dependencies + git hooks
make check        # lint, types, architecture, tests - what CI runs
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/); the `commit-msg`
hook enforces it. Releases are automatic: every push to `main` runs semantic-release, which
bumps the version from the commits (`feat` -> minor, `fix` -> patch, `!` -> major), writes
`CHANGELOG.md`, tags `vX.Y.Z` and publishes the Docker image to GHCR. The first release of a
repository is `1.0.0`; push a tag such as `v0.1.0` first to start lower.

Architecture rules are documented in `docs/` and enforced by `scripts/archcheck.py`. Add a
feature the way `docs/guides/add-a-feature` describes. {pkg} was started from
[python-clean-architecture-template](https://github.com/{template}).
"""

README = """# {pkg}

Built from [python-clean-architecture-template](https://github.com/{template}).

```bash
make install     # dependencies + git hooks
make run         # migrations + API with reload -> http://localhost:8000/docs
make check       # lint, types, architecture (dependency rule), tests
```

## Add a feature

```bash
uv run python scripts/new_feature.py orders
```

creates `src/{pkg}/orders/` (domain, application, infrastructure, http), wires it in
`src/{pkg}/bootstrap/features/orders.py` and writes `tests/test_orders.py`.

## Layout

```text
src/{pkg}/
├── shared/        building blocks reused by every feature
├── <feature>/     domain -> application -> infrastructure | http | cli
├── bootstrap/     settings, app factory, transaction/event middlewares, features/
└── main.py        uvicorn {pkg}.main:app
```

Dependencies point inward; `scripts/archcheck.py check` (part of `make check`) fails
otherwise. The architecture and its decisions are documented in `docs/`.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--name", help="new package name (lowercase identifier)")
    parser.add_argument("--remove-example", action="store_true")
    args = parser.parse_args()

    pkg = CURRENT_PACKAGE
    if args.name and args.name != CURRENT_PACKAGE:
        rename_package(args.name)
        pkg = args.name
    strip_template_only()
    if args.remove_example:
        remove_example(pkg)
    rebrand(pkg)
    write_readme(pkg)

    if ruff := shutil.which("ruff"):  # tidy imports/blank lines left behind by the edits
        subprocess.run([ruff, "check", "--fix", "-q", str(ROOT)], check=False)
        subprocess.run([ruff, "format", "-q", str(ROOT)], check=False)
    if (ROOT / "docs" / "docs" / "architecture" / "dependency-graph.md").exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "graph.py")], check=False)
    if uv := shutil.which("uv"):  # the project name changed: the lockfile must follow
        subprocess.run([uv, "lock", "--quiet"], cwd=ROOT, check=False)
    Path(__file__).unlink()  # one-shot: the project is yours now
    print("done - review with `git diff`, then: make check")
    print("next: uv run python scripts/new_feature.py <your_feature>")


if __name__ == "__main__":
    main()
