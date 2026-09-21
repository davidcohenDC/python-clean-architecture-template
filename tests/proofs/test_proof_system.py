"""The proof system must itself be falsifiable.

* a broken mapping (ADR or README citing a proof that does not exist, tests marked
  with an unknown id) is detected;
* PASS is only ever the result of a test that ran and passed;
* a deliberate architecture violation turns `make proof` red with exit code 1.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.proofs.registry import Proof, problems
from tests.proofs.runner import FAIL, NO_EVIDENCE, PASS, SKIPPED, Outcome, Registry, verdicts

ROOT = Path(__file__).resolve().parents[2]

# -- a minimal, consistent repository layout the registry rules can be run against -----


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def sound(tmp_path: Path) -> Path:
    write(tmp_path, "proofs.toml", '[alpha]\ntitle = "Alpha"\nclaim = "A"\nadr = ["001"]\n')
    write(
        tmp_path,
        "tests/test_alpha.py",
        'import pytest\n\n@pytest.mark.proof("alpha")\ndef test_a(): ...\n',
    )
    write(tmp_path, "docs/docs/decisions/001-alpha.md", "# ADR\n\n## Proof\n\n- proof:alpha\n")
    write(
        tmp_path,
        "docs/docs/decisions/002-tech.md",
        "# ADR\n\n## Proof\n\nNo executable proof: tech.\n",
    )
    write(tmp_path, "README.md", "| `proof:alpha` | ... |\n")
    assert problems(tmp_path) == []
    return tmp_path


def test_an_adr_citing_a_nonexistent_proof_is_detected(sound):
    write(sound, "docs/docs/decisions/002-tech.md", "# ADR\n\n## Proof\n\n- proof:ghost\n")
    assert any("unknown proof 'ghost'" in p for p in problems(sound))


def test_an_adr_without_a_proof_statement_is_detected(sound):
    write(sound, "docs/docs/decisions/002-tech.md", "# ADR\n\nJust prose.\n")
    assert any("ADR 002 declares neither" in p for p in problems(sound))


def test_a_registry_adr_reference_must_be_reciprocated(sound):
    write(
        sound, "docs/docs/decisions/001-alpha.md", "# ADR\n\n## Proof\n\nNo executable proof: x.\n"
    )
    assert any("ADR 001 does not reference proof:alpha" in p for p in problems(sound))


def test_a_test_marked_with_an_unknown_proof_is_detected(sound):
    write(
        sound,
        "tests/test_ghost.py",
        'import pytest\n\n@pytest.mark.proof("ghost")\ndef test_g(): ...\n',
    )
    assert any("unknown proof 'ghost'" in p for p in problems(sound))


def test_readme_must_cite_every_proof_and_only_existing_ones(sound):
    write(sound, "README.md", "| `proof:beta` |\n")
    found = problems(sound)
    assert any("README cites unknown proof 'beta'" in p for p in found)
    assert any("README does not mention proof:alpha" in p for p in found)


# -- verdict aggregation: PASS is never the default ---------------------------------------


def registry(*ids: str) -> Registry:
    return Registry({pid: Proof(pid, pid, pid) for pid in ids})


def test_a_proof_nothing_ran_for_is_no_evidence_not_pass():
    assert verdicts(registry("alpha"), {})["alpha"].verdict == NO_EVIDENCE


@pytest.mark.parametrize(
    ("outcome", "verdict"),
    [
        (Outcome(passed=3), PASS),
        (Outcome(passed=3, failed=1), FAIL),
        (Outcome(passed=3, skipped=1), SKIPPED),
        (Outcome(skipped=2), SKIPPED),
    ],
)
def test_one_failure_or_skip_taints_the_whole_proof(outcome, verdict):
    assert verdicts(registry("alpha"), {"alpha": outcome})["alpha"].verdict == verdict


# -- dogfooding: an intentional violation turns `make proof` red ---------------------------


def run_proof(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(cwd / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    for leaked in ("PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST"):
        env.pop(leaked, None)
    return subprocess.run(
        [sys.executable, "scripts/proof.py", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.contract
def test_a_dependency_violation_makes_the_proof_red(tmp_path: Path):
    copy = tmp_path / "repo"
    for name in (
        "src",
        "tests",
        "scripts",
        "docs/docs",
        "proofs.toml",
        "README.md",
        "pyproject.toml",
    ):
        source = ROOT / name
        (copy / name).parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, copy / name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, copy / name)
    write(
        copy,
        "src/cleanarch/tournaments/domain/_smuggled.py",
        "from cleanarch.tournaments.infrastructure.in_memory import InMemoryTournamentRepository\n",
    )

    result = run_proof(copy, "tests/architecture", f"--basetemp={copy / '.pt'}")

    assert result.returncode == 1, result.stdout[-3000:]
    assert "Dependency rule" in result.stdout and "FAIL" in result.stdout
    assert "_smuggled" in result.stdout, "the report names the offending module"


@pytest.mark.contract
def test_running_no_evidence_is_not_a_pass(tmp_path: Path):
    result = run_proof(ROOT, "-k", "no_such_test_anywhere", f"--basetemp={tmp_path / 'pt'}")
    assert result.returncode == 1
    assert "0/" in result.stdout and NO_EVIDENCE in result.stdout
