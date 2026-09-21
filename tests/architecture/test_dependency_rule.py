"""The Dependency Rule applied to the real package.

The checker itself lives in ``dependency_rule.py`` and is falsified by
``test_self_check.py``. This test only asks it about ``cleanarch``.
"""

from pathlib import Path

import pytest
from archcheck import check

import cleanarch

pytestmark = [
    pytest.mark.proof("dependency-rule", "feature-isolation"),
]

ROOT = Path(cleanarch.__file__).parent


def test_the_package_respects_the_dependency_rule():
    """The Dependency Rule and feature isolation, checked on the real package."""
    violations = check(ROOT, "cleanarch")
    assert violations == [], "\n" + "\n".join(str(v) for v in violations)
