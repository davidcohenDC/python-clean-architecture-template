#!/usr/bin/env python
"""Turn the template into *your* project. Run it once, right after cloning.

    uv run python scripts/init_project.py --name shopapi --remove-example

* ``--name``            renames the Python package (``cleanarch`` -> ``shopapi``)
                        everywhere: source, tests, alembic, Docker, Makefile, docs.
* ``--remove-example``  deletes the ``tournaments`` feature (its package, its
                        bootstrap module, its tests, its migrations).

Whatever the flags, it also removes what only makes sense in the template
repository - its self-tests, the proof registry, the marketing README - and
writes a short README for the new project. The result is a project that is
green on ``make check`` and ready for ``scripts/new_feature.py``.

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
]

# The example feature: one package, one bootstrap module, one test folder, its migrations.
EXAMPLE_PATHS = [
    "src/{pkg}/" + EXAMPLE,
    "src/{pkg}/bootstrap/features/" + EXAMPLE + ".py",
    "tests/" + EXAMPLE,
]
EXAMPLE_MIGRATIONS = "alembic/versions"

TEMPLATE_BLOCK = re.compile(
    r"^[ \t]*(#|<!--)[ ]*>>> template-only.*?^[ \t]*(#|<!--)[ ]*<<< template-only[^\n]*\n",
    re.DOTALL | re.MULTILINE,
)


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
    settings = ROOT / "src" / new / "bootstrap" / "settings.py"
    replacements = [
        (ROOT / "pyproject.toml", 'name = "python-clean-architecture-template"', f'name = "{new}"'),
        (
            settings,
            'app_name: str = "python-clean-architecture-template"',
            f'app_name: str = "{new}"',
        ),
    ]
    for path, old, fresh in replacements:
        path.write_text(path.read_text(encoding="utf-8").replace(old, fresh, 1), encoding="utf-8")
    print(f"renamed package {CURRENT_PACKAGE} -> {new}")


def strip_template_only() -> None:
    for relative in TEMPLATE_ONLY:
        remove(relative)
    for path in text_files():
        content = path.read_text(encoding="utf-8")
        updated = TEMPLATE_BLOCK.sub("", content)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
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
    print(f"removed the {EXAMPLE} example (package, bootstrap module, tests, migrations)")


def write_readme(pkg: str) -> None:
    (ROOT / "README.md").write_text(
        f"""# {pkg}

Built from [python-clean-architecture-template](https://github.com/davidcohenDC/python-clean-architecture-template).

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
""",
        encoding="utf-8",
    )


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
    write_readme(pkg)

    if ruff := shutil.which("ruff"):  # tidy imports/blank lines left behind by the edits
        subprocess.run([ruff, "check", "--fix", "-q", str(ROOT)], check=False)
        subprocess.run([ruff, "format", "-q", str(ROOT)], check=False)
    if (ROOT / "docs" / "docs" / "architecture" / "dependency-graph.md").exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "graph.py")], check=False)
    print("done - review with `git diff`, then: make check")
    print("next: uv run python scripts/new_feature.py <your_feature>")


if __name__ == "__main__":
    main()
