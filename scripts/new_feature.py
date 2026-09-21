#!/usr/bin/env python
"""Scaffold a new feature with all four rings and a working vertical slice.

    uv run python scripts/new_feature.py orders

creates ``src/<package>/orders/`` with an ``Order`` entity, a repository port,
two use cases (create/get), an in-memory adapter and a FastAPI router; wires
it in ``bootstrap/features/orders.py`` (listed in ``FEATURES``); and writes a
first test in ``tests/test_orders.py``. ``make check`` is green and
``POST /api/v1/orders`` works before you change a line. Then replace the
placeholder fields with your model.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def package_name() -> str:
    packages = [p.name for p in SRC.iterdir() if (p / "bootstrap").is_dir()]
    if len(packages) != 1:
        sys.exit(f"Expected exactly one package under src/, found {packages}")
    return packages[0]


def singular(plural: str) -> str:
    if plural.endswith("ies"):
        return plural[:-3] + "y"
    if plural.endswith("s") and not plural.endswith("ss"):
        return plural[:-1]
    return plural


def pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def render(pkg: str, feature: str) -> dict[str, str]:
    entity = pascal(singular(feature))  # orders -> Order
    var = singular(feature)  # order
    f = feature
    return {
        "__init__.py": f'"""{entity} feature: domain -> application -> infrastructure / http."""\n',
        "domain/__init__.py": f"""from {pkg}.{f}.domain.errors import Invalid{entity}Name
from {pkg}.{f}.domain.events import {entity}Created
from {pkg}.{f}.domain.{var} import {entity}, {entity}Id, new_{var}_id

__all__ = ["Invalid{entity}Name", "{entity}", "{entity}Created", "{entity}Id", "new_{var}_id"]
""",
        "domain/errors.py": f"""from {pkg}.shared.domain.errors import DomainError


class Invalid{entity}Name(DomainError):
    message = "{entity} name cannot be blank."
""",
        "domain/events.py": f"""from dataclasses import dataclass

from {pkg}.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True)
class {entity}Created(DomainEvent):
    {var}_id: str
    name: str
""",
        f"domain/{var}.py": f'''"""The ``{entity}`` aggregate root (placeholder fields)."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import NewType

from {pkg}.shared.domain.result import DomainResult
from {pkg}.{f}.domain.errors import Invalid{entity}Name
from {pkg}.{f}.domain.events import {entity}Created

{entity}Id = NewType("{entity}Id", str)


def new_{var}_id() -> {entity}Id:
    return {entity}Id(uuid.uuid4().hex)


@dataclass(frozen=True, slots=True)
class {entity}:
    id: {entity}Id
    name: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise Invalid{entity}Name

    @classmethod
    def create(cls, name: str, *, created_at: datetime) -> DomainResult["{entity}"]:
        {var} = cls(id=new_{var}_id(), name=name, created_at=created_at)
        return DomainResult.of({var}, {entity}Created({var}.id, {var}.name))
''',
        "application/__init__.py": f"""from {pkg}.{f}.application.errors import {entity}NotFound
from {pkg}.{f}.application.ports import {entity}Repository
from {pkg}.{f}.application.use_cases import Create{entity}, Get{entity}

__all__ = ["Create{entity}", "Get{entity}", "{entity}NotFound", "{entity}Repository"]
""",
        "application/errors.py": f"""from {pkg}.shared.application.errors import NotFoundError


class {entity}NotFound(NotFoundError):
    def __init__(self, {var}_id: str) -> None:
        super().__init__(f"{entity} '{{{var}_id}}' not found.")
""",
        "application/ports.py": f"""from typing import Protocol

from {pkg}.{f}.domain import {entity}, {entity}Id


class {entity}Repository(Protocol):
    async def add(self, {var}: {entity}) -> None: ...

    async def get(self, {var}_id: {entity}Id) -> {entity} | None: ...
""",
        "application/use_cases.py": f"""from {pkg}.shared.application.ports import Clock
from {pkg}.shared.application.ports import EventPublisher
from {pkg}.{f}.application.errors import {entity}NotFound
from {pkg}.{f}.application.ports import {entity}Repository
from {pkg}.{f}.domain import {entity}, {entity}Id


class Create{entity}:
    def __init__(
        self, repository: {entity}Repository, events: EventPublisher, clock: Clock
    ) -> None:
        self._repository = repository
        self._events = events
        self._clock = clock

    async def execute(self, name: str) -> {entity}:
        result = {entity}.create(name, created_at=self._clock.now())
        await self._repository.add(result.aggregate)
        await self._events.publish(result.events)
        return result.aggregate


class Get{entity}:
    def __init__(self, repository: {entity}Repository) -> None:
        self._repository = repository

    async def execute(self, {var}_id: {entity}Id) -> {entity}:
        {var} = await self._repository.get({var}_id)
        if {var} is None:
            raise {entity}NotFound({var}_id)
        return {var}
""",
        "infrastructure/__init__.py": "",
        "infrastructure/in_memory.py": f"""from {pkg}.{f}.domain import {entity}, {entity}Id


class InMemory{entity}Repository:
    def __init__(self) -> None:
        self._rows: dict[{entity}Id, {entity}] = {{}}

    async def add(self, {var}: {entity}) -> None:
        self._rows[{var}.id] = {var}

    async def get(self, {var}_id: {entity}Id) -> {entity} | None:
        return self._rows.get({var}_id)
""",
        "http/__init__.py": f"""from {pkg}.{f}.http.dependencies import get_{var}_repository
from {pkg}.{f}.http.router import router

__all__ = ["get_{var}_repository", "router"]
""",
        "http/dependencies.py": f"""from typing import Annotated

from fastapi import Depends

from {pkg}.shared.application.ports import Clock, EventPublisher
from {pkg}.shared.http.dependencies import get_clock, get_event_publisher
from {pkg}.{f}.application import Create{entity}, Get{entity}, {entity}Repository


def get_{var}_repository() -> {entity}Repository:
    raise NotImplementedError("Provided by {pkg}.bootstrap (dependency_overrides)")


Repository = Annotated[{entity}Repository, Depends(get_{var}_repository)]
Events = Annotated[EventPublisher, Depends(get_event_publisher)]
Now = Annotated[Clock, Depends(get_clock)]


def create_{var}(repository: Repository, events: Events, clock: Now) -> Create{entity}:
    return Create{entity}(repository, events, clock)


def get_{var}(repository: Repository) -> Get{entity}:
    return Get{entity}(repository)
""",
        "http/schemas.py": f"""from datetime import datetime
from typing import Self

from {pkg}.shared.http.schemas import Schema
from {pkg}.{f}.domain import {entity}


class Create{entity}Request(Schema):
    name: str


class {entity}Response(Schema):
    id: str
    name: str
    created_at: datetime

    @classmethod
    def from_domain(cls, {var}: {entity}) -> Self:
        return cls(id={var}.id, name={var}.name, created_at={var}.created_at)
""",
        "http/router.py": f"""from typing import Annotated

from fastapi import APIRouter, Depends, status

from {pkg}.{f}.application import Create{entity}, Get{entity}
from {pkg}.{f}.domain import {entity}Id
from {pkg}.{f}.http import dependencies as deps
from {pkg}.{f}.http.schemas import Create{entity}Request, {entity}Response

router = APIRouter(prefix="/{f}", tags=["{f}"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model={entity}Response)
async def create(
    body: Create{entity}Request,
    use_case: Annotated[Create{entity}, Depends(deps.create_{var})],
) -> {entity}Response:
    return {entity}Response.from_domain(await use_case.execute(body.name))


@router.get("/{{{var}_id}}", response_model={entity}Response)
async def get(
    {var}_id: str,
    use_case: Annotated[Get{entity}, Depends(deps.get_{var})],
) -> {entity}Response:
    return {entity}Response.from_domain(await use_case.execute({entity}Id({var}_id)))
""",
    }


def render_bootstrap(pkg: str, feature: str) -> str:
    """``bootstrap/features/<feature>.py``: where the feature meets the outside world."""
    entity, var, f = pascal(singular(feature)), singular(feature), feature
    return f'''"""Everything the {f} feature needs from the outside world."""

from fastapi import FastAPI

from {pkg}.bootstrap.settings import Settings
from {pkg}.{f}.http import get_{var}_repository, router
from {pkg}.{f}.infrastructure.in_memory import InMemory{entity}Repository


def wire_http(app: FastAPI, settings: Settings) -> None:
    # In-memory for now. Add a SQLAlchemy adapter and pick it when
    # ``not settings.use_in_memory`` (see the template's example feature).
    repository = InMemory{entity}Repository()
    app.dependency_overrides[get_{var}_repository] = lambda: repository
    app.include_router(router, prefix="/api/v1")
'''


def render_test(pkg: str, feature: str) -> str:
    """``tests/test_<feature>.py``: a use case with fakes and the HTTP boundary."""
    entity, f = pascal(singular(feature)), feature
    return f'''"""First tests for {f}. Move or rewrite them freely."""

import pytest

from {pkg}.shared.infrastructure.clock import FixedClock
from {pkg}.{f}.application import Create{entity}
from {pkg}.{f}.domain import Invalid{entity}Name
from {pkg}.{f}.infrastructure.in_memory import InMemory{entity}Repository
from tests.conftest import NOW, RecordingEventPublisher


async def test_create_persists_and_publishes():
    repository, events = InMemory{entity}Repository(), RecordingEventPublisher()

    created = await Create{entity}(repository, events, FixedClock(NOW)).execute("first")

    assert await repository.get(created.id) == created
    assert [type(e).__name__ for e in events.events] == ["{entity}Created"]


async def test_blank_name_is_a_domain_error():
    repository, events = InMemory{entity}Repository(), RecordingEventPublisher()
    use_case = Create{entity}(repository, events, FixedClock(NOW))
    with pytest.raises(Invalid{entity}Name):
        await use_case.execute("  ")


async def test_http_round_trip(client):
    created = await client.post("/api/v1/{f}", json={{"name": "first"}})
    assert created.status_code == 201, created.text

    fetched = await client.get(f"/api/v1/{f}/{{created.json()['id']}}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "first"
'''


def register_feature(pkg: str, feature: str) -> bool:
    """Import the module in ``bootstrap/features/__init__.py`` and list it in ``FEATURES``."""
    init = SRC / pkg / "bootstrap" / "features" / "__init__.py"
    text = init.read_text(encoding="utf-8")
    match = re.search(r"^FEATURES(: [^=]+)? = \[(\]?)", text, flags=re.M)
    if match is None:
        return False
    import_line = f"from {pkg}.bootstrap.features import {feature}\n\n"
    opening = match.group(0).rstrip("]")
    entry = f"{feature}]" if match.group(2) else f"{feature}, "
    text = text[: match.start()] + import_line + opening + entry + text[match.end() :]
    init.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"[a-z][a-z0-9_]*", sys.argv[1]):
        sys.exit("usage: new_feature.py <snake_case_plural_name>   e.g. orders")
    feature = sys.argv[1]
    pkg = package_name()
    target = SRC / pkg / feature
    if target.exists():
        sys.exit(f"{target} already exists")

    for relative, content in render(pkg, feature).items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    bootstrap_module = SRC / pkg / "bootstrap" / "features" / f"{feature}.py"
    bootstrap_module.write_text(render_bootstrap(pkg, feature), encoding="utf-8")
    registered = register_feature(pkg, feature)
    test_file = ROOT / "tests" / f"test_{feature}.py"
    if not test_file.exists():
        test_file.write_text(render_test(pkg, feature), encoding="utf-8")

    touched = [target, bootstrap_module, bootstrap_module.parent / "__init__.py", test_file]
    if ruff := shutil.which("ruff"):  # sort imports for whatever name was chosen
        subprocess.run([ruff, "check", "--fix", "-q", *map(str, touched)], check=False)
        subprocess.run([ruff, "format", "-q", *map(str, touched)], check=False)

    print(f"Created {target.relative_to(ROOT)}")
    wired = "yes" if registered else "NO - add it to FEATURES by hand"
    print(f"        {bootstrap_module.relative_to(ROOT)}  (wired: {wired})")
    print(f"        {test_file.relative_to(ROOT)}")
    print()
    print("Next steps:")
    print("  1. make check                      # lint, types, architecture, tests: green")
    print(f"  2. make run-memory                 # POST /api/v1/{feature} works")
    print(f"  3. Replace the placeholder fields in {target.relative_to(ROOT)}/domain/")
    print("  4. Add a SQLAlchemy adapter + migration when you need persistence.")


if __name__ == "__main__":
    main()
