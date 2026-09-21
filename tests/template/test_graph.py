"""The committed dependency graph must be the one the code produces."""

from pathlib import Path

import pytest
from archcheck import page

import cleanarch

pytestmark = pytest.mark.architecture

ROOT = Path(cleanarch.__file__).parent
PAGE = (
    Path(__file__).resolve().parents[2] / "docs" / "docs" / "architecture" / "dependency-graph.md"
)


def test_the_generated_graph_page_is_up_to_date():
    assert PAGE.read_text(encoding="utf-8") == page(ROOT, "cleanarch"), (
        "docs/docs/architecture/dependency-graph.md is stale: run `make graph`"
    )
