"""The mapping claim -> evidence -> decision -> README must be sound on this repository."""

from pathlib import Path

from tests.template.proofs.registry import problems

ROOT = Path(__file__).resolve().parents[3]


def test_the_proof_registry_is_consistent():
    found = problems(ROOT)
    assert found == [], "\n" + "\n".join(found)
