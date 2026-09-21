"""The Dependency Rule applied to the real package.

The checker itself lives in ``dependency_rule.py`` and is falsified by
``test_self_check.py``. This test only asks it about ``cleanarch``.
"""

from pathlib import Path

import pytest

import cleanarch
from tests.architecture.dependency_rule import check

pytestmark = pytest.mark.architecture

ROOT = Path(cleanarch.__file__).parent


def test_the_package_respects_the_dependency_rule():
    violations = check(ROOT, "cleanarch")
    assert violations == [], "\n" + "\n".join(str(v) for v in violations)
