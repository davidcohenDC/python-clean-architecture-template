#!/usr/bin/env python
"""``make proof``: run the executable architecture guarantees and print the verdict.

Usage:  uv run python scripts/proof.py [extra pytest args]
Exit:   0 all guarantees passed · 1 a guarantee failed or lacks evidence · 2 registry inconsistent
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.template.proofs.runner import main  # noqa: E402 - needs the path above

if __name__ == "__main__":
    sys.exit(main(ROOT, sys.argv[1:]))
