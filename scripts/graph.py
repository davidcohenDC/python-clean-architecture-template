#!/usr/bin/env python
"""``make graph``: regenerate docs/docs/architecture/dependency-graph.md from the code."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.architecture.graph import page  # noqa: E402 - needs the path above

PACKAGES = [p for p in (ROOT / "src").iterdir() if (p / "bootstrap").is_dir()]
if len(PACKAGES) != 1:
    sys.exit(f"expected exactly one package under src/, found {[p.name for p in PACKAGES]}")

target = ROOT / "docs" / "docs" / "architecture" / "dependency-graph.md"
target.write_text(page(PACKAGES[0], PACKAGES[0].name), encoding="utf-8")
print(f"wrote {target.relative_to(ROOT)}")
