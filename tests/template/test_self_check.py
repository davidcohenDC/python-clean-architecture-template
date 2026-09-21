"""Falsify the checker: build tiny packages with one deliberate violation each.

If any of these stops failing, the Dependency Rule has a hole - which is
exactly what the checker exists to prevent.
"""

from pathlib import Path

import pytest
from archcheck import Violation, check

pytestmark = pytest.mark.architecture


def src(*lines: str) -> str:
    return "\n".join(lines) + "\n"


CLEAN = {
    "shared/domain/errors.py": src("class DomainError(Exception): ..."),
    "shared/application/ports.py": src("from typing import Protocol", "class Clock(Protocol): ..."),
    "shared/infrastructure/clock.py": src("from datetime import UTC, datetime"),
    "shared/http/errors.py": src(
        "from fastapi import FastAPI", "from pkg.shared.domain.errors import DomainError"
    ),
    "orders/domain/__init__.py": src("from pkg.orders.domain.order import Order"),
    "orders/domain/order.py": src(
        "from dataclasses import dataclass", "from pkg.shared.domain.errors import DomainError"
    ),
    "orders/application/ports.py": src(
        "from typing import Protocol", "from pkg.orders.domain import Order"
    ),
    "orders/application/use_cases.py": src(
        "from pkg.orders.application.ports import OrderRepository",
        "from pkg.shared.application.ports import Clock",
    ),
    "orders/infrastructure/in_memory.py": src("from pkg.orders.domain import Order"),
    "orders/infrastructure/sqlalchemy/repository.py": src(
        "from sqlalchemy import select", "from pkg.orders.application.ports import OrderRepository"
    ),
    "orders/http/router.py": src(
        "from fastapi import APIRouter", "from pkg.orders.application.use_cases import CreateOrder"
    ),
    "orders/cli/commands.py": src(
        "import argparse", "from pkg.orders.application.use_cases import CreateOrder"
    ),
    "bootstrap/app.py": src(
        "from pkg.orders.http.router import router",
        "from pkg.orders.infrastructure.sqlalchemy.repository import Repo",
        "from pkg.shared.infrastructure.clock import SystemClock",
    ),
    "main.py": src("from pkg.bootstrap.app import create_app"),
}


def make_package(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "pkg"
    for relative, source in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        for parent in [path.parent, *path.parents]:
            if parent == root.parent:
                break
            (parent / "__init__.py").touch()
        path.write_text(source, encoding="utf-8")
    return root


def violations_for(tmp_path: Path, extra: dict[str, str]) -> list[Violation]:
    return check(make_package(tmp_path, {**CLEAN, **extra}), "pkg")


@pytest.mark.proof("dependency-rule", "feature-isolation")
def test_a_clean_package_has_no_violations(tmp_path):
    assert check(make_package(tmp_path, CLEAN), "pkg") == []


RING_CASES = [
    (
        "domain imports infrastructure (absolute)",
        "orders/domain/rule.py",
        src("from pkg.orders.infrastructure.in_memory import Repo"),
        "outer ring",
    ),
    (
        "domain imports infrastructure (relative)",
        "orders/domain/rule.py",
        src("from ..infrastructure.in_memory import Repo"),
        "outer ring",
    ),
    (
        "import hidden inside a function",
        "orders/domain/rule.py",
        src("def f():", "    from pkg.orders.http.router import router"),
        "outer ring",
    ),
    (
        "import under TYPE_CHECKING still couples",
        "orders/application/service.py",
        src(
            "from typing import TYPE_CHECKING",
            "if TYPE_CHECKING:",
            "    from pkg.orders.infrastructure.in_memory import Repo",
        ),
        "outer ring",
    ),
    (
        "multi-segment plain import",
        "orders/domain/rule.py",
        src("import pkg.orders.infrastructure.sqlalchemy.repository"),
        "outer ring",
    ),
    (
        "submodule imported as a name",
        "orders/domain/rule.py",
        src("from pkg.orders import infrastructure"),
        "outer ring",
    ),
    (
        "domain __init__ re-exports application",
        "orders/domain/__init__.py",
        src("from pkg.orders.application.ports import OrderRepository"),
        "outer ring",
    ),
    (
        "application imports http",
        "orders/application/service.py",
        src("from pkg.orders.http.router import router"),
        "outer ring",
    ),
    (
        "http imports infrastructure (sibling adapters)",
        "orders/http/deps.py",
        src("from pkg.orders.infrastructure.in_memory import Repo"),
        "wired together in bootstrap",
    ),
    (
        "cli imports http (sibling adapters)",
        "orders/cli/extra.py",
        src("from pkg.orders.http.router import router"),
        "wired together in bootstrap",
    ),
    (
        "domain imports a framework",
        "orders/domain/rule.py",
        src("from pydantic import BaseModel"),
        "third-party",
    ),
    (
        "application imports any third-party library",
        "orders/application/service.py",
        src("import requests"),
        "third-party",
    ),
    (
        "module in an unknown ring",
        "orders/utils/helpers.py",
        src("x = 1"),
        "not a known ring",
    ),
]

ISOLATION_CASES = [
    (
        "feature imports another feature",
        "orders/application/service.py",
        src("from pkg.billing.domain.invoice import Invoice"),
        "cross-feature",
    ),
    (
        "shared imports a feature",
        "shared/application/helper.py",
        src("from pkg.orders.domain import Order"),
        "'shared' must not know about features",
    ),
]


def _assert_caught(tmp_path, description, file, source, reason):
    found = violations_for(tmp_path, {file: source})
    assert found, f"not caught: {description}"
    assert any(reason in v.reason for v in found), f"{description}: {[str(v) for v in found]}"


@pytest.mark.proof("dependency-rule")
@pytest.mark.parametrize(
    ("description", "file", "source", "reason"), RING_CASES, ids=[c[0] for c in RING_CASES]
)
def test_each_ring_violation_is_caught(tmp_path, description, file, source, reason):
    _assert_caught(tmp_path, description, file, source, reason)


@pytest.mark.proof("feature-isolation")
@pytest.mark.parametrize(
    ("description", "file", "source", "reason"),
    ISOLATION_CASES,
    ids=[c[0] for c in ISOLATION_CASES],
)
def test_each_isolation_violation_is_caught(tmp_path, description, file, source, reason):
    _assert_caught(tmp_path, description, file, source, reason)


def test_stdlib_and_inner_rings_are_always_allowed(tmp_path):
    extra = {
        "orders/domain/rule.py": src(
            "import uuid",
            "from datetime import datetime",
            "from pkg.shared.domain.errors import DomainError",
        ),
        "orders/http/extra.py": src(
            "from pkg.orders.domain import Order", "from pkg.shared.http.errors import x"
        ),
        "bootstrap/cli.py": src("from pkg.orders.cli.commands import register"),
    }
    assert violations_for(tmp_path, extra) == []


@pytest.mark.proof("dependency-rule")
def test_the_message_names_module_import_and_remedy(tmp_path):
    (found,) = violations_for(
        tmp_path, {"orders/domain/rule.py": src("from pkg.orders.http.router import router")}
    )
    assert str(found) == (
        "pkg.orders.domain.rule imports pkg.orders.http.router: "
        "'http' is an outer ring; invert the dependency with a port"
    )
