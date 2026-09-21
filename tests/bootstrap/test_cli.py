"""The command-line composition root, exercised with a stub feature (no example involved).

Every feature module may offer ``register_cli``/``run_cli``/``subscribe``; the CLI builds
the parser from them, runs one command inside ``transaction()`` and dispatches the
collected events after the commit - the same unit of work as an HTTP request.
"""

import argparse
import asyncio
import types
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cleanarch.bootstrap import cli
from cleanarch.shared.domain.errors import DomainError
from cleanarch.shared.domain.events import DomainEvent
from cleanarch.shared.infrastructure.events import CollectedEvents, InProcessEventBus
from tests.conftest import make_settings


@dataclass(frozen=True, slots=True, kw_only=True)
class Pinged(DomainEvent):
    note: str


class Broken(DomainError):
    message = "Boom."


def stub_feature(handled: list[str]) -> types.ModuleType:
    """A feature with one ``ping`` command that writes a row, publishes an event, or fails."""
    feature = types.ModuleType("stub")

    def register_cli(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        ping = subparsers.add_parser("ping")
        ping.add_argument("note")

    async def run_cli(args: argparse.Namespace, session: AsyncSession, events: CollectedEvents):
        if args.feature != "ping":
            return False
        await session.execute(text("CREATE TABLE IF NOT EXISTS pings (note TEXT)"))
        await session.execute(text("INSERT INTO pings VALUES (:note)"), {"note": args.note})
        if args.note == "fail":
            raise Broken
        await events.publish([Pinged(note=args.note)])
        return True

    def subscribe(bus: InProcessEventBus) -> None:
        async def on_pinged(event: Pinged) -> None:
            handled.append(event.note)

        bus.subscribe(Pinged, on_pinged)

    feature.register_cli = register_cli  # type: ignore[attr-defined]
    feature.run_cli = run_cli  # type: ignore[attr-defined]
    feature.subscribe = subscribe  # type: ignore[attr-defined]
    return feature


@pytest.fixture
def handled(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    notes: list[str] = []
    feature = stub_feature(notes)
    monkeypatch.setattr(cli, "FEATURES", [feature])
    monkeypatch.setattr("cleanarch.bootstrap.events.FEATURES", [feature])
    return notes


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'cli.db'}"


async def rows(db_url: str) -> list[str]:
    engine = cli.make_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT note FROM pings"))
            return [row[0] for row in result]
    finally:
        await engine.dispose()


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]):
    assert cli.main([], make_settings(database_url="memory://")) == 2
    assert "usage:" in capsys.readouterr().out


def test_version_flag():
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"], make_settings())
    assert exit_info.value.code == 0


def test_the_in_memory_backend_is_refused(handled: list[str]):
    with pytest.raises(SystemExit, match="memory://"):
        cli.main(["ping", "hello"], make_settings(database_url="memory://"))


def test_a_command_commits_then_its_events_are_dispatched(handled: list[str], db_url: str):
    assert cli.main(["ping", "hello"], make_settings(database_url=db_url)) == 0
    assert asyncio.run(rows(db_url)) == ["hello"]
    assert handled == ["hello"]


def test_a_domain_error_rolls_back_and_is_reported(
    handled: list[str], db_url: str, capsys: pytest.CaptureFixture[str]
):
    settings = make_settings(database_url=db_url)
    assert cli.main(["ping", "first"], settings) == 0
    assert cli.main(["ping", "fail"], settings) == 1
    assert "error: Boom." in capsys.readouterr().err
    assert asyncio.run(rows(db_url)) == ["first"]  # the failed command's row is gone
    assert handled == ["first"]  # and its event was never dispatched


def test_a_command_nobody_runs_is_an_error(
    handled: list[str], db_url: str, monkeypatch: pytest.MonkeyPatch
):
    mute = stub_feature([])
    del mute.run_cli  # registers the command, never runs it
    monkeypatch.setattr(cli, "FEATURES", [mute])
    with pytest.raises(SystemExit, match="no feature handles 'ping'"):
        cli.main(["ping", "hello"], make_settings(database_url=db_url))
