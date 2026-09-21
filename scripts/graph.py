#!/usr/bin/env python
"""``make graph``: regenerate docs/docs/architecture/dependency-graph.md from the code."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from archcheck import find_package, page  # noqa: E402 - needs the path above

package = find_package(ROOT)
target = ROOT / "docs" / "docs" / "architecture" / "dependency-graph.md"
target.write_text(page(package, package.name), encoding="utf-8")
print(f"wrote {target.relative_to(ROOT)}")
