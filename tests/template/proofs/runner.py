"""``make proof``: run the evidence, report one line per guarantee.

The runner is a thin pytest plugin. It selects only tests marked
``@pytest.mark.proof(...)``, records every outcome per proof id and prints a
table. A proof is PASS only when at least one of its tests ran and passed and
none failed or was skipped: nothing is green by default.
"""

import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.template.proofs.registry import Registry, load, problems

PASS, FAIL, SKIPPED, NO_EVIDENCE = "PASS", "FAIL", "SKIPPED", "NO EVIDENCE"


@dataclass
class Outcome:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.failed:
            return FAIL
        if self.skipped:
            return SKIPPED
        return PASS if self.passed else NO_EVIDENCE


class ProofCollector:
    """pytest plugin: keep only proof-marked tests and tally their results per proof id."""

    def __init__(self) -> None:
        self.outcomes: dict[str, Outcome] = defaultdict(Outcome)
        self._ids_of: dict[str, tuple[str, ...]] = {}

    def pytest_collection_modifyitems(
        self, config: pytest.Config, items: list[pytest.Item]
    ) -> None:
        selected = []
        for item in items:
            ids = tuple(pid for mark in item.iter_markers("proof") for pid in mark.args)
            if ids:
                self._ids_of[item.nodeid] = ids
                selected.append(item)
        config.hook.pytest_deselected(items=[i for i in items if i not in selected])
        items[:] = selected

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        ids = self._ids_of.get(report.nodeid, ())
        if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
            for pid in ids:
                outcome = self.outcomes[pid]
                if report.outcome == "passed":
                    outcome.passed += 1
                elif report.outcome == "skipped":
                    outcome.skipped += 1
                else:
                    outcome.failed += 1
                    outcome.failures.append(report.nodeid)


def verdicts(registry: Registry, outcomes: dict[str, Outcome]) -> dict[str, Outcome]:
    """One outcome per registered proof, NO EVIDENCE when nothing ran for it."""
    return {pid: outcomes.get(pid, Outcome()) for pid in registry.proofs}


def render(registry: Registry, results: dict[str, Outcome], seconds: float) -> str:
    width = max(len(p.title) for p in registry.proofs.values()) + 2
    lines = ["ARCHITECTURE PROOF", ""]
    for pid, outcome in results.items():
        proof = registry.proofs[pid]
        adr = ", ".join(f"ADR-{n}" for n in proof.adr) or "no ADR"
        lines.append(f"  {proof.title:<{width}} {outcome.verdict:<12} {adr}")
        for nodeid in outcome.failures:
            lines.append(f"      x {nodeid}")
    passed = sum(1 for o in results.values() if o.verdict == PASS)
    lines += ["", f"{passed}/{len(results)} executable guarantees passed in {seconds:.1f}s"]
    if any(o.verdict == NO_EVIDENCE for o in results.values()):
        lines.append(
            "NO EVIDENCE: no test marked @pytest.mark.proof('<id>') ran for that guarantee. "
            "Mark the tests of your feature that prove it, or drop it from proofs.toml."
        )
    lines += [
        "Each line is one falsifiable property backed by real tests (proofs.toml).",
        "It is not a proof that the architecture is correct; it is what is checked.",
    ]
    return "\n".join(lines)


def main(root: Path, argv: list[str] | None = None) -> int:
    registry = load(root)
    inconsistencies = problems(root)
    if inconsistencies:
        print("PROOF REGISTRY IS INCONSISTENT\n")
        for line in inconsistencies:
            print(f"  x {line}")
        return 2

    collector = ProofCollector()
    extra = list(argv or [])
    paths = [] if any(not a.startswith("-") for a in extra) else ["tests"]
    started = time.perf_counter()
    pytest.main(
        [*paths, "-q", "-p", "no:cacheprovider", "--no-header", "-o", "addopts=", *extra],
        plugins=[collector],
    )
    results = verdicts(registry, collector.outcomes)
    print()
    print(render(registry, results, time.perf_counter() - started))
    return 0 if all(o.verdict == PASS for o in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(Path(__file__).resolve().parents[3], sys.argv[1:]))
