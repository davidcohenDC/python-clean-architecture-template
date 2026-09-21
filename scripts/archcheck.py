#!/usr/bin/env python
"""Architecture guardrail: the Dependency Rule as a small, readable static checker.

    python scripts/archcheck.py check   # exit 1 with one line per violation
    python scripts/archcheck.py graph   # Mermaid graph of the real imports between rings

Source code dependencies must point *inward*:

    domain  <-  application  <-  infrastructure | http | cli  <-  bootstrap

The tool parses every module of the package under ``src/`` with ``ast`` (no
imports executed). It is deliberately a script, not a test: it does not care
how you organise your tests, and ``make check`` / CI run it directly. If you
want it inside pytest as well, ``tests/architecture/test_dependency_rule.py``
is the one-line way.

What counts as an import: ``import a.b``, ``from a import b`` (where ``b`` may
be a submodule), relative imports, imports inside functions and inside
``if TYPE_CHECKING:`` blocks. Type-only imports still couple modules; a port
is the way to depend on an outer ring, not ``TYPE_CHECKING``.

Adding a ring (say ``consumers/``): add it to ``RING`` with its position.
"""

import ast
import sys
from collections import defaultdict
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


# -- graph: the same parser, drawn ------------------------------------------------

STYLE = {
    "domain": "#16a34a",
    "application": "#2563eb",
    "infrastructure": "#d97706",
    "http": "#d97706",
    "cli": "#d97706",
    "bootstrap": "#6b7280",
    "main": "#6b7280",
    "__main__": "#6b7280",
}


def edges(root: Path, package: str) -> dict[tuple[str, str], set[str]]:
    """``{(from_node, to_node): {feature names that create the edge}}`` at ring granularity."""
    found: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in sorted(root.rglob("*.py")):
        parts = list(path.relative_to(root.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        module = ".".join(parts)
        here = locate(module, package)
        if here is None or here.layer is None:
            continue
        for imported in imports_of(path, module, package):
            there = locate(imported, package)
            if there is None or there.layer is None:
                continue
            source, target = _node(here.feature, here.layer), _node(there.feature, there.layer)
            if source != target:
                found[(source, target)].add(here.feature or "")
    return found


def _node(feature: str | None, layer: str) -> str:
    return "bootstrap" if layer in COMPOSITION else f"{feature}.{layer}"


def mermaid(root: Path, package: str) -> str:
    graph = edges(root, package)
    nodes = sorted({n for edge in graph for n in edge})
    lines = ["flowchart LR"]
    for node in nodes:
        lines.append(f'    {_id(node)}["{node}"]')
    for source, target in sorted(graph):
        lines.append(f"    {_id(source)} --> {_id(target)}")
    for node in nodes:
        layer = node.rsplit(".", 1)[-1]
        lines.append(
            f"    style {_id(node)} fill:{STYLE.get(layer, '#999')},color:#fff,stroke:none"
        )
    return "\n".join(lines) + "\n"


def _id(node: str) -> str:
    return node.replace(".", "_").replace("__", "x")


def page(root: Path, package: str) -> str:  # the docs page written by scripts/graph.py
    return (
        "---\n"
        "id: dependency-graph\n"
        "title: Dependency graph (generated)\n"
        "sidebar_position: 6\n"
        "---\n\n"
        "# Dependency graph, generated from the code\n\n"
        "Every arrow below is a real `import` found by the same parser that enforces the\n"
        "[Dependency Rule](testing#architecture-a-tool-and-optionally-a-test) - not a\n"
        "drawing of intent. Regenerate with `make graph`; in the template repository\n"
        "`tests/template/test_graph.py` fails when this file is stale.\n\n"
        "```mermaid\n" + mermaid(root, package) + "```\n"
    )


# -- command line ------------------------------------------------------------------


def find_package(root: Path) -> Path:
    packages = [p for p in (root / "src").iterdir() if (p / "bootstrap").is_dir()]
    if len(packages) != 1:
        sys.exit(f"expected exactly one package under src/, found {[p.name for p in packages]}")
    return packages[0]


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    command = argv[0] if argv else "check"
    package_dir = find_package(root)
    if command == "graph":
        print(mermaid(package_dir, package_dir.name), end="")
        return 0
    if command != "check":
        print(__doc__)
        return 2
    violations = check(package_dir, package_dir.name)
    modules = sum(1 for _ in package_dir.rglob("*.py"))
    if violations:
        print(f"ARCHITECTURE: {len(violations)} violation(s) in {package_dir.name}")
        print()
        for violation in violations:
            print(f"  x {violation}")
        return 1
    print(f"ARCHITECTURE OK: {modules} modules of '{package_dir.name}' point inward")
    print("  domain < application < {infrastructure, http, cli} < bootstrap")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
