"""The Dependency Rule as a small, readable static checker.

Source code dependencies must point *inward*:

    domain  <-  application  <-  infrastructure | http | cli  <-  bootstrap

``check(root, package)`` parses every module of a package with ``ast`` (no
imports executed) and returns the violations it finds. It is used against the
real package by ``test_dependency_rule.py`` and against small synthetic trees
with deliberate violations by ``test_self_check.py`` - the rule is only worth
something if it can be shown to fail.

What counts as an import: ``import a.b``, ``from a import b`` (where ``b`` may
be a submodule), relative imports, imports inside functions and inside
``if TYPE_CHECKING:`` blocks. Type-only imports still couple modules; a port
is the way to depend on an outer ring, not ``TYPE_CHECKING``.
"""

import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# Inner rings have lower numbers. Adapters (infrastructure, http, cli) share ring 2
# but may not import each other: they are wired together in bootstrap.
RING: dict[str, int] = {
    "domain": 0,
    "application": 1,
    "infrastructure": 2,
    "http": 2,
    "cli": 2,
    "bootstrap": 3,
    "main": 3,
    "__main__": 3,
}
COMPOSITION = {"bootstrap", "main", "__main__"}

# Frameworks and I/O libraries that must never leak into the inner rings.
OUTER_WORLD = {
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_settings",
    "sqlalchemy",
    "alembic",
    "aiosqlite",
    "asyncpg",
    "httpx",
    "uvicorn",
}


@dataclass(frozen=True, slots=True)
class Violation:
    module: str
    imported: str
    reason: str

    def __str__(self) -> str:
        return f"{self.module} imports {self.imported}: {self.reason}"


@dataclass(frozen=True, slots=True)
class Location:
    """Where a module (or an imported name) sits: ``<package>.<feature>.<layer>...``."""

    feature: str | None
    layer: str | None

    @property
    def ring(self) -> int | None:
        return RING.get(self.layer or "")


def locate(dotted: str, package: str) -> Location | None:
    """``pkg.orders.domain.x`` -> Location('orders', 'domain'); ``None`` if outside the package."""
    parts = dotted.split(".")
    if parts[0] != package:
        return None
    if len(parts) < 2:
        return Location(None, None)
    if parts[1] in COMPOSITION:
        return Location(parts[1], parts[1])
    return Location(parts[1], parts[2] if len(parts) > 2 else None)


def imports_of(path: Path, module: str, package: str) -> Iterator[str]:
    """Every dotted name a module imports, relative imports resolved, submodules included."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    container = module if path.name == "__init__.py" else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base = node.module or ""
            else:
                parents = container.split(".")
                parents = parents[: len(parents) - node.level + 1]
                base = ".".join([*parents, node.module] if node.module else parents)
            yield base
            where = locate(base, package)
            if where is not None and where.layer is None:
                for alias in node.names:  # ``from pkg.orders import infrastructure``
                    yield f"{base}.{alias.name}"


def check(root: Path, package: str) -> list[Violation]:
    """Return every Dependency Rule violation under ``root`` (the package directory)."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        parts = list(path.relative_to(root.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        module = ".".join(parts)
        here = locate(module, package)
        assert here is not None
        if here.layer is None:  # <package>/__init__.py or <package>/<feature>/__init__.py
            continue
        if here.ring is None:
            violations.append(
                Violation(
                    module,
                    "-",
                    f"'{here.layer}' is not a known ring {sorted(RING)}; move the module "
                    "or add the ring to RING with its position",
                )
            )
            continue
        for imported in imports_of(path, module, package):
            violations.extend(_judge(module, here, imported, package))
    return violations


def _judge(module: str, here: Location, imported: str, package: str) -> Iterator[Violation]:
    there = locate(imported, package)
    top = imported.split(".")[0]

    if there is None:  # outside the package: stdlib is fine everywhere, libraries only outside
        inner = here.ring is not None and here.ring <= 1
        if inner and (top in OUTER_WORLD or top not in sys.stdlib_module_names):
            yield Violation(
                module, imported, f"'{top}' is third-party; inner rings depend on nothing"
            )
        return

    if here.feature not in (None, "shared", *COMPOSITION) and there.feature not in (
        None,
        "shared",
        here.feature,
    ):
        yield Violation(
            module,
            imported,
            "cross-feature import; move what you share into 'shared' or talk through a port",
        )
        return
    if here.feature == "shared" and there.feature not in (None, "shared"):
        yield Violation(module, imported, "'shared' must not know about features")
        return

    if there.ring is None or here.ring is None:
        return
    if there.ring > here.ring:
        yield Violation(
            module,
            imported,
            f"'{there.layer}' is an outer ring; invert the dependency with a port",
        )
    elif there.ring == here.ring == 2 and there.layer != here.layer:
        yield Violation(
            module, imported, "adapters are wired together in bootstrap, never directly"
        )
