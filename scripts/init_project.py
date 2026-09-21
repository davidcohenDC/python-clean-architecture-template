#!/usr/bin/env python
"""Turn the template into *your* project.

    uv run python scripts/init_project.py --name shopapi --remove-example

* ``--name``            renames the Python package (``cleanarch`` -> ``shopapi``)
                        everywhere: source, tests, alembic, Dockerfile, Makefile, docs.
* ``--remove-example``  deletes the tournaments feature, its tests and its
                        migration, and strips the blocks between
                        ``>>> example`` / ``<<< example`` markers.

Run it once, right after cloning. It is safe to run on a clean git tree and
easy to review with ``git diff``.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT_PACKAGE = "cleanarch"

TEXT_GLOBS = [
    "pyproject.toml",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "alembic.ini",
    "release.config.mjs",
    "README.md",
    "CONTRIBUTING.md",
    "alembic/**/*.py",
    "src/**/*.py",
    "tests/**/*.py",
    "scripts/**/*.py",
    "docs/docs/**/*.md",
    "docs/docs/**/*.mdx",
    ".github/**/*.yml",
    ".github/**/*.md",
]

EXAMPLE_PATHS = [
    "src/{pkg}/tournaments",
    "tests/domain/test_phases.py",
    "tests/domain/test_progress.py",
    "tests/domain/test_tournament.py",
    "tests/application/test_use_cases.py",
    "tests/integration/test_tournament_repository_contract.py",
    "tests/api/test_auth.py",
    "tests/api/test_events.py",
    "tests/api/test_tournament_errors.py",
    "tests/api/test_tournaments_api.py",
    "tests/api/test_transaction.py",
    "tests/cli/test_cli.py",
]

# Every migration shipped with the template belongs to the example: the template itself
# owns no tables. Removing the example therefore empties the chain instead of cherry-picking.
EXAMPLE_MIGRATIONS = "alembic/versions"

MARKER = re.compile(
    r"^[ \t]*# >>> example: tournaments\n.*?^[ \t]*# <<< example: tournaments\n",
    re.DOTALL | re.MULTILINE,
)


def text_files() -> list[Path]:
    files: list[Path] = []
    for pattern in TEXT_GLOBS:
        files.extend(p for p in ROOT.glob(pattern) if p.is_file())
    return files


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
    print(f"renamed package {CURRENT_PACKAGE} -> {new}")


def remove_example(pkg: str) -> None:
    for relative in EXAMPLE_PATHS:
        path = ROOT / relative.format(pkg=pkg)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    for migration in (ROOT / EXAMPLE_MIGRATIONS).glob("*.py"):
        migration.unlink()
    for path in text_files():
        content = path.read_text(encoding="utf-8")
        updated = MARKER.sub("", content)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
    print("removed the tournaments example feature (and its migrations: the chain is empty)")
    print("next: uv run python scripts/new_feature.py <your_feature>")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--name", help="new package name (lowercase identifier)")
    parser.add_argument("--remove-example", action="store_true")
    args = parser.parse_args()
    if not args.name and not args.remove_example:
        parser.error("nothing to do: pass --name and/or --remove-example")

    pkg = CURRENT_PACKAGE
    if args.name and args.name != CURRENT_PACKAGE:
        rename_package(args.name)
        pkg = args.name
    if args.remove_example:
        remove_example(pkg)
    if ruff := shutil.which("ruff"):  # tidy imports/blank lines left behind by the edits
        subprocess.run([ruff, "check", "--fix", "-q", str(ROOT)], check=False)
        subprocess.run([ruff, "format", "-q", str(ROOT)], check=False)
    print("done - review with `git diff`, then run `make check`")


if __name__ == "__main__":
    main()
