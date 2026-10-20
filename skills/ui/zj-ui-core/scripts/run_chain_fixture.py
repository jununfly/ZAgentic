"""Chain-level fixture harness for the `zj-ui-*` closed loop (roadmap 1-6-5).

A chain fixture is a checked-in `input.json` (a `chain_request`) / `expected.json`
pair. It asserts the orchestrator's end-to-end guarantee: resolver-gated
execution, artifact threading, freeze-or-stop with zero downstream writes.

Usage:
    python run_chain_fixture.py <fixture-dir>            # one, human summary
    python run_chain_fixture.py <root> --recursive       # every chain fixture
    python run_chain_fixture.py --list                   # embedded fixture list
Exit code is 0 only when every fixture matches its expectation.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ui_chain  # noqa: E402


def load(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def compare(observed: dict, expected: dict) -> list:
    problems = []

    for field in ("chain_status", "stopped_at", "total_writes"):
        if field in expected and observed.get(field) != expected[field]:
            problems.append(
                f"{field}: expected {expected[field]!r}, got {observed.get(field)!r}"
            )

    if "plan_hash_count" in expected:
        got = len(observed.get("plan_hashes", []))
        if got != expected["plan_hash_count"]:
            problems.append(
                f"plan_hash_count: expected {expected['plan_hash_count']}, got {got}"
            )

    if "produced_artifact_kinds" in expected:
        want = list(expected["produced_artifact_kinds"])
        got = list(observed.get("produced_artifacts", []))
        if want != got:
            problems.append(f"produced_artifact_kinds: expected {want}, got {got}")

    return problems


def run_chain_fixture(directory: pathlib.Path) -> dict:
    request = load(directory / "input.json")
    expected = load(directory / "expected.json")
    observed = ui_chain.run_chain(request)
    return {
        "fixture_id": request.get("fixture_id", directory.name),
        "problems": compare(observed, expected),
        "observed": observed,
    }


def fixture_dirs(root: pathlib.Path) -> list:
    if (root / "input.json").is_file():
        return [root]
    return sorted(path.parent for path in root.rglob("input.json"))


def main(argv) -> int:
    recursive = "--recursive" in argv
    targets = [arg for arg in argv[1:] if not arg.startswith("--")]
    if not targets:
        print(__doc__)
        return 2

    root = pathlib.Path(targets[0])
    directories = fixture_dirs(root) if recursive else [root]
    failed = 0
    for directory in directories:
        report = run_chain_fixture(directory)
        if report["problems"]:
            failed += 1
            print(f"[FAIL] {report['fixture_id']} -> {report['observed']['chain_status']}")
            for problem in report["problems"]:
                print(f"       {problem}")
        else:
            print(
                f"[ok] {report['fixture_id']} -> {report['observed']['chain_status']} "
                f"(writes={report['observed']['total_writes']}, "
                f"artifacts={len(report['observed']['produced_artifacts'])})"
            )

    print(f"\n{len(directories) - failed}/{len(directories)} chain fixtures matched")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
