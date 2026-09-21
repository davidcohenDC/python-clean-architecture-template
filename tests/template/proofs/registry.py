"""The proof registry and its consistency rules.

Three sources must agree:

* ``proofs.toml``          - the claims (id, title, claim, adr);
* ``@pytest.mark.proof``   - the evidence, found by scanning the test files with ``ast``;
* ``docs/docs/decisions``  - every ADR states ``proof:<id>`` lines or ``No executable proof: ...``;
* ``README.md``            - may only cite ids that exist, and must cite every id.

``problems(root)`` returns a list of human-readable inconsistencies; empty means
the mapping is sound. It never runs a test: soundness of the *mapping* and truth
of the *claims* are two different checks (see ``runner.py`` for the second).
"""

import ast
import re
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

PROOF_REF = re.compile(r"proof:([a-z0-9-]+)")
NO_PROOF = re.compile(r"^No executable proof: \S", re.MULTILINE)
ADR_ID = re.compile(r"^(\d{3})-.*\.md$")


@dataclass(frozen=True)
class Proof:
    id: str
    title: str
    claim: str
    adr: tuple[str, ...] = ()


@dataclass
class Registry:
    proofs: dict[str, Proof]
    evidence: dict[str, list[str]] = field(default_factory=dict)  # id -> test files


def load(root: Path) -> Registry:
    data = tomllib.loads((root / "proofs.toml").read_text(encoding="utf-8"))
    proofs = {
        pid: Proof(pid, entry["title"], entry["claim"], tuple(entry.get("adr", ())))
        for pid, entry in data.items()
    }
    return Registry(proofs, evidence=marked_tests(root / "tests"))


def marked_tests(tests_dir: Path) -> dict[str, list[str]]:
    """``{proof_id: [test files that carry @pytest.mark.proof(proof_id)]}`` via ``ast``."""
    found: dict[str, list[str]] = {}
    for path in sorted(tests_dir.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in ast.walk(tree):
            if not (isinstance(call, ast.Call) and _is_proof_marker(call.func)):
                continue
            for arg in call.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.setdefault(arg.value, []).append(path.as_posix())
    return found


def _is_proof_marker(node: ast.expr) -> bool:
    # pytest.mark.proof(...)  or  mark.proof(...)
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "proof"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
    )


def adr_files(root: Path) -> dict[str, Path]:
    decisions = root / "docs" / "docs" / "decisions"
    files = {}
    for path in sorted(decisions.glob("*.md")):
        match = ADR_ID.match(path.name)
        if match:
            files[match.group(1)] = path
    return files


def problems(root: Path) -> list[str]:
    registry = load(root)
    return list(_problems(registry, root))


def _problems(registry: Registry, root: Path) -> Iterator[str]:
    ids = set(registry.proofs)

    # evidence -> registry (a proof *without* evidence is not a mapping error: the runner
    # reports it as NO EVIDENCE, which is what a freshly stripped project must see)
    for pid, files in registry.evidence.items():
        if pid not in ids:
            yield f"tests {sorted(set(files))} are marked with unknown proof '{pid}'"

    # ADRs <-> registry (bidirectional)
    adrs = adr_files(root)
    for pid, proof in registry.proofs.items():
        for number in proof.adr:
            if number not in adrs:
                yield f"proof '{pid}' references ADR {number}, which does not exist"
            elif f"proof:{pid}" not in adrs[number].read_text(encoding="utf-8"):
                yield f"ADR {number} does not reference proof:{pid} but the registry lists it"
    for number, path in adrs.items():
        text = path.read_text(encoding="utf-8")
        cited = set(PROOF_REF.findall(text))
        if not cited and not NO_PROOF.search(text):
            yield f"ADR {number} declares neither a proof:<id> nor 'No executable proof: <reason>'"
        for pid in cited - ids:
            yield f"ADR {number} references unknown proof '{pid}'"
        for pid in cited & ids:
            if number not in registry.proofs[pid].adr:
                yield f"ADR {number} cites proof:{pid} but the registry does not list that ADR"

    # README <-> registry
    readme = (root / "README.md").read_text(encoding="utf-8")
    cited = set(PROOF_REF.findall(readme))
    for pid in sorted(cited - ids):
        yield f"README cites unknown proof '{pid}'"
    for pid in sorted(ids - cited):
        yield f"README does not mention proof:{pid}; every guarantee must be visible there"
