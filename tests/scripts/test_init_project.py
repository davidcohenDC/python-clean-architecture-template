"""The example-removal contract, executed for real on a temporary copy.

``scripts/init_project.py --name <pkg> --remove-example`` must leave a project that
lints, type-checks at the import level, passes the architecture tests, migrates from
an empty database and serves ``/health``. This test runs those steps end to end so
the contract cannot silently rot when the example grows.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[2]
COPIED = [
    "src",
    "tests",
    "alembic",
    "scripts",
    "pyproject.toml",
    "alembic.ini",
    "release.config.mjs",
    "README.md",
    "Makefile",
]


def run(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=False)


@pytest.fixture(scope="module")
def stripped_project(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, str]]:
    target = tmp_path_factory.mktemp("stripped")
    for name in COPIED:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, target / name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, target / name)
    env = {
        **os.environ,
        "PYTHONPATH": str(target / "src"),
        "DATABASE_URL": f"sqlite+aiosqlite:///{target / 'fresh.db'}",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.pop("API_KEYS", None)
    result = run(
        sys.executable,
        "scripts/init_project.py",
        "--name",
        "acme",
        "--remove-example",
        cwd=target,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return target, env


def test_no_functional_reference_to_the_example_survives(stripped_project):
    target, _ = stripped_project
    survivors = [
        path
        for path in (target / "src").rglob("*.py")
        if "tournament" in path.read_text(encoding="utf-8").lower()
    ]
    assert survivors == []
    assert not (target / "src" / "acme" / "tournaments").exists()
    assert list((target / "alembic" / "versions").glob("*.py")) == []


def test_stripped_project_lints_and_passes_the_architecture_tests(stripped_project):
    target, env = stripped_project
    lint = run(sys.executable, "-m", "ruff", "check", "src", "tests", cwd=target, env=env)
    assert lint.returncode == 0, lint.stdout
    tests = run(
        sys.executable,
        "-m",
        "pytest",
        "tests/architecture",
        "-q",
        "-p",
        "no:cacheprovider",
        cwd=target,
        env=env,
    )
    assert tests.returncode == 0, tests.stdout[-2000:]


def test_stripped_project_migrates_from_an_empty_database_and_serves_health(stripped_project):
    target, env = stripped_project
    migrate = run(sys.executable, "-m", "alembic", "upgrade", "head", cwd=target, env=env)
    assert migrate.returncode == 0, migrate.stderr[-2000:]

    probe = (
        "import asyncio, httpx\n"
        "from acme.bootstrap import create_app\n"
        "app = create_app()\n"
        "async def main():\n"
        "    async with app.router.lifespan_context(app):\n"
        "        t = httpx.ASGITransport(app=app)\n"
        "        async with httpx.AsyncClient(transport=t, base_url='http://t') as c:\n"
        "            r = await c.get('/health'); assert r.status_code == 200, r.text\n"
        "            r = await c.get('/ready'); assert r.status_code == 200, r.text\n"
        "            r = await c.get('/api/v1/tournaments'); assert r.status_code == 404, r.text\n"
        "asyncio.run(main())\n"
    )
    served = run(sys.executable, "-c", probe, cwd=target, env=env)
    assert served.returncode == 0, served.stderr[-2000:]
