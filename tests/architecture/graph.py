"""A Mermaid graph of the *actual* dependencies between rings, from the same parser
that enforces the Dependency Rule. One source of truth: if the checker and the
picture ever disagree, the checker is wrong too."""

from collections import defaultdict
from pathlib import Path

from tests.architecture.dependency_rule import COMPOSITION, imports_of, locate

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


def page(root: Path, package: str) -> str:
    return (
        "---\n"
        "id: dependency-graph\n"
        "title: Dependency graph (generated)\n"
        "sidebar_position: 6\n"
        "---\n\n"
        "# Dependency graph, generated from the code\n\n"
        "Every arrow below is a real `import` found by the same parser that enforces the\n"
        "[Dependency Rule](testing#architecture-tests) - not a drawing of intent. Regenerate\n"
        "with `make graph`; `tests/architecture/test_graph.py` fails when the file is stale.\n\n"
        "```mermaid\n" + mermaid(root, package) + "```\n"
    )
