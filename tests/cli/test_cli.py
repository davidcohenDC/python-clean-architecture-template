"""The CLI drives the same use cases as HTTP, through the same ports, on a real SQLite file."""

import asyncio
from pathlib import Path

import pytest

from cleanarch.bootstrap import Settings
from cleanarch.bootstrap.cli import main
from cleanarch.shared.infrastructure.database import Base, make_engine
from tests.conftest import make_settings

pytestmark = pytest.mark.api


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    url = f"sqlite+aiosqlite:///{tmp_path / 'cli.db'}"

    async def create_schema() -> None:
        engine = make_engine(url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_schema())
    return make_settings(database_url=url)


def run(settings: Settings, *argv: str, capsys) -> tuple[int, str, str]:
    code = main(list(argv), settings=settings)
    captured = capsys.readouterr()
    return code, captured.out.strip(), captured.err.strip()


def test_create_list_start_advance(settings, capsys):
    code, out, _ = run(
        settings, "tournaments", "create", "Spring Cup", "--rounds", "1", capsys=capsys
    )
    assert code == 0
    tournament_id = out.split()[0]
    assert "'Spring Cup'  not_started" in out

    code, out, _ = run(settings, "tournaments", "list", capsys=capsys)
    assert code == 0 and tournament_id in out

    code, out, _ = run(settings, "tournaments", "start", tournament_id, capsys=capsys)
    assert code == 0 and "in_progress phase 0 round 0" in out

    code, out, _ = run(settings, "tournaments", "advance", tournament_id, capsys=capsys)
    assert code == 0 and "finished" in out


def test_domain_errors_are_exit_code_1_with_a_message(settings, capsys):
    _, out, _ = run(settings, "tournaments", "create", "Cup", capsys=capsys)
    tournament_id = out.split()[0]

    code, _, err = run(settings, "tournaments", "advance", tournament_id, capsys=capsys)

    assert code == 1
    assert err == "error: Tournament has not started yet."


def test_unknown_id_is_a_clean_error(settings, capsys):
    code, _, err = run(settings, "tournaments", "get", "nope", capsys=capsys)
    assert code == 1
    assert "not found" in err


def test_memory_backend_is_refused(capsys):
    with pytest.raises(SystemExit):
        main(["tournaments", "list"], settings=make_settings(database_url="memory://"))
