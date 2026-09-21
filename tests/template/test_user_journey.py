"""The user journey, executed for real on a temporary copy (TEMPLATE-ONLY).

    use template -> init (rename, remove example) -> green project -> first feature -> green

Every step runs the commands a user runs. If this passes, a fresh project works.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.proof("example-removal")]

ROOT = Path(__file__).resolve().parents[2]
COPIED = [
    "src",
    "tests",
    "alembic",
    "scripts",
    "docs/docs",
    "docs/docusaurus.config.ts",
    "docs/sidebars.ts",
    "package.json",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    ".env.example",
    ".github",
    ".githooks",
    "proofs.toml",
    "pyproject.toml",
    "alembic.ini",
    "release.config.mjs",
    "README.md",
    "Makefile",
    "uv.lock",
    ".pre-commit-config.yaml",
]
PY = sys.executable
TEMPLATE_WORDS = (
    "cleanarch",
    "proof:",
    "proofs.toml",
    "make proof",
    "mark.proof",
    "template-only",
    "example-only",
)
ATTRIBUTION = {"README.md", "CONTRIBUTING.md", "docs/docs/intro.md"}  # "built from ..." is fine


def run(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def assert_green(cwd: Path, env: dict[str, str], basetemp: Path) -> None:
    """What ``make check`` runs, on the copy."""
    for command in (
        (PY, "-m", "ruff", "check", "src", "tests", "scripts"),
        (PY, "-m", "ruff", "format", "--check", "src", "tests", "scripts"),
        (PY, "-m", "mypy"),
        (PY, "scripts/archcheck.py", "check"),
        (PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", f"--basetemp={basetemp}"),
    ):
        result = run(*command, cwd=cwd, env=env)
        assert result.returncode == 0, f"{' '.join(command[1:])}\n{result.stdout[-2500:]}"


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, str]]:
    target = tmp_path_factory.mktemp("acme")
    for name in COPIED:
        source = ROOT / name
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target / name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, target / name)
    env = {
        **os.environ,
        "PYTHONPATH": str(target / "src"),
        "DATABASE_URL": "sqlite+aiosqlite:///./fresh.db",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for leaked in ("API_KEYS", "PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST"):
        env.pop(leaked, None)
    init = run(
        PY, "scripts/init_project.py", "--name", "acme", "--remove-example", cwd=target, env=env
    )
    assert init.returncode == 0, init.stderr
    return target, env


def test_init_leaves_nothing_of_the_example_or_of_the_template_checks(project):
    target, _ = project
    survivors = [
        p for p in (target / "src").rglob("*.py") if "tournament" in p.read_text(encoding="utf-8")
    ]
    assert survivors == []
    for gone in ("tests/template", "tests/tournaments", "proofs.toml", "scripts/proof.py"):
        assert not (target / gone).exists(), gone
    assert list((target / "alembic" / "versions").glob("*.py")) == []
    assert "template-only" not in (target / "Makefile").read_text(encoding="utf-8")
    assert "proof" not in (target / ".github/workflows/build-and-deploy.yml").read_text(
        encoding="utf-8"
    )
    assert (target / "README.md").read_text(encoding="utf-8").startswith("# acme\n")


def test_init_leaves_no_trace_of_the_template_repository(project):
    target, _ = project
    leaks: list[str] = []
    for path in target.rglob("*"):
        relative = path.relative_to(target).as_posix()
        if not path.is_file() or "__pycache__" in relative or relative == "uv.lock":
            continue
        if path.suffix in (".db", ".pyc"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if "python-clean-architecture-template" in text and relative not in ATTRIBUTION:
            leaks.append(f"{relative}: template repository")
        leaks.extend(f"{relative}: {word}" for word in TEMPLATE_WORDS if word in text)
    assert leaks == [], "\n".join(leaks)


def test_a_fresh_project_is_green(project, tmp_path: Path):
    target, env = project
    assert_green(target, env, tmp_path / "pt")
    migrate = run(PY, "-m", "alembic", "upgrade", "head", cwd=target, env=env)
    assert migrate.returncode == 0, migrate.stderr[-2000:]


def test_the_first_feature_is_green_and_served(project, tmp_path: Path):
    target, env = project
    scaffold = run(PY, "scripts/new_feature.py", "orders", cwd=target, env=env)
    assert scaffold.returncode == 0, scaffold.stderr
    assert "wired: yes" in scaffold.stdout

    assert_green(target, env, tmp_path / "pt")

    probe = (
        "import asyncio, httpx\n"
        "from acme.bootstrap import create_app\n"
        "app = create_app()\n"
        "async def main():\n"
        "    async with app.router.lifespan_context(app):\n"
        "        t = httpx.ASGITransport(app=app)\n"
        "        async with httpx.AsyncClient(transport=t, base_url='http://t') as c:\n"
        "            r = await c.post('/api/v1/orders', json={'name': 'first'})\n"
        "            assert r.status_code == 201, r.text\n"
        "            r = await c.get('/ready'); assert r.status_code == 200, r.text\n"
        "asyncio.run(main())\n"
    )
    served = run(PY, "-c", probe, cwd=target, env={**env, "DATABASE_URL": "memory://"})
    assert served.returncode == 0, served.stderr[-2000:]
