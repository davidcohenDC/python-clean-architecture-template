"""The Dependency Rule, executable.

Source code dependencies must point *inward*:

    domain  <-  application  <-  infrastructure | http | cli  <-  bootstrap

These tests parse every module under ``cleanarch`` with ``ast`` (no import
side effects, no third-party tooling) and fail with a readable message the
moment someone imports an outer ring from an inner one. They are deliberately
written as plain pytest so you can read exactly what "Clean" means here.
"""

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import cleanarch

pytestmark = pytest.mark.architecture

PACKAGE = "cleanarch"
ROOT = Path(cleanarch.__file__).parent

# Inner rings have lower numbers. ``infrastructure`` and ``http`` are siblings:
# same ring, but neither may import the other.
RING = {
    "domain": 0,
    "application": 1,
    "infrastructure": 2,
    "http": 2,
    "cli": 2,
    "bootstrap": 3,
    "main": 3,
    "__main__": 3,
}

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


class Module:
    def __init__(self, path: Path) -> None:
        self.path = path
        relative = path.relative_to(ROOT.parent).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts.pop()
        self.name = ".".join(parts)
        # cleanarch.<feature>.<layer>... | cleanarch.bootstrap... | cleanarch.main
        self.feature = parts[1] if len(parts) > 1 else None
        if self.feature in ("bootstrap", "main", "__main__"):
            self.layer: str | None = self.feature
        else:
            self.layer = parts[2] if len(parts) > 2 else None

    @property
    def ring(self) -> int | None:
        return RING.get(self.layer or "")

    def imports(self) -> Iterator[str]:
        """Absolute module names, with relative imports (``from ..x import y``) resolved."""
        tree = ast.parse(self.path.read_text(encoding="utf-8"), filename=str(self.path))
        package = self.name if self.path.name == "__init__.py" else self.name.rpartition(".")[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                yield from (alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    yield node.module or ""
                    continue
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                yield ".".join([*base, node.module] if node.module else base)

    def __repr__(self) -> str:
        return self.name


def all_modules() -> list[Module]:
    return [Module(p) for p in sorted(ROOT.rglob("*.py"))]


def parse(imported: str) -> tuple[str | None, str | None]:
    """``cleanarch.tournaments.domain.x`` -> ('tournaments', 'domain')."""
    parts = imported.split(".")
    if parts[0] != PACKAGE or len(parts) < 2:
        return None, None
    if parts[1] in ("bootstrap", "main", "__main__"):
        return parts[1], parts[1]
    return parts[1], parts[2] if len(parts) > 2 else None


MODULES = all_modules()
ids = [m.name for m in MODULES]


@pytest.mark.parametrize("module", MODULES, ids=ids)
def test_every_module_belongs_to_a_ring(module: Module):
    """An unknown ring under ``cleanarch/<feature>/`` is a hole in the rule, not a free pass."""
    if module.layer is None:  # cleanarch/__init__.py or cleanarch/<feature>/__init__.py
        return
    assert module.layer in RING, (
        f"{module} lives in '{module.layer}', which is not a known ring {sorted(RING)}. "
        "Move it, or add the ring to RING with its position."
    )


@pytest.mark.parametrize("module", MODULES, ids=ids)
def test_dependencies_point_inward(module: Module):
    """A module may only import from its own ring or an inner one."""
    if module.ring is None:  # package __init__ of a feature, or cleanarch/__init__
        return
    for imported in module.imports():
        _, layer = parse(imported)
        if layer is None or layer not in RING:
            continue
        assert RING[layer] <= module.ring, (
            f"{module} ({module.layer}) imports {imported} ({layer}): "
            f"'{layer}' is an outer ring. Invert the dependency with a port."
        )
        if RING[layer] == module.ring and layer != module.layer and module.ring == 2:
            pytest.fail(
                f"{module} ({module.layer}) imports {imported} ({layer}): "
                "adapters are wired together in bootstrap, never directly."
            )


@pytest.mark.parametrize("module", MODULES, ids=ids)
def test_inner_rings_do_not_know_frameworks(module: Module):
    """``domain`` and ``application`` are plain Python: stdlib + this package only."""
    if module.ring is None or module.ring > 1:
        return
    for imported in module.imports():
        top = imported.split(".")[0]
        assert top not in OUTER_WORLD, f"{module} imports {imported}"
        assert top == PACKAGE or top in sys.stdlib_module_names, (
            f"{module} imports third-party '{top}'. Inner rings depend on nothing."
        )


@pytest.mark.parametrize("module", MODULES, ids=ids)
def test_features_are_isolated(module: Module):
    """``shared`` never imports a feature; a feature never imports another feature."""
    if module.feature in (None, "bootstrap", "main", "__main__"):
        return
    for imported in module.imports():
        feature, _ = parse(imported)
        if feature in (None, "shared"):
            continue
        assert feature == module.feature, (
            f"{module} imports {imported}: cross-feature imports are forbidden. "
            "Move what you need into 'shared' or talk through a port."
        )
