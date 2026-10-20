"""Fixture harness for the `zj-ui-*` chain.

A fixture is a checked-in `input.json` / `expected.json` pair. It exists so the
sentence "missing `success_criteria` becomes `NEEDS_CONTEXT` with zero writes"
cannot be quietly edited away: the fixture is the assertion, and any change to
the sentence has to show up as a red comparison here.

Usage:
    python run_fixture.py <fixture-dir>          # one fixture, human summary
    python run_fixture.py <dir> --json           # machine-readable
    python run_fixture.py <root> --recursive     # every fixture below <root>
    python run_fixture.py --list-stages          # what this build implements
Exit code is 0 only when every fixture matches its expectation.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ui_stages  # noqa: E402


def load(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def dig(payload, dotted: str):
    """Resolve `a.b[0].c`; raises KeyError/IndexError like normal access."""
    current = payload
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", dotted):
        if part.startswith("["):
            current = current[int(part[1:-1])]
        else:
            current = current[part]
    return current


def missing(payload, dotted: str) -> bool:
    try:
        dig(payload, dotted)
    except (KeyError, IndexError, TypeError):
        return True
    return False


def run_request(stage: str, request: dict) -> dict:
    runner = ui_stages.STAGES.get(stage)
    if runner is None:
        raise SystemExit(f"no implementation for stage {stage!r}; have {sorted(ui_stages.STAGES)}")
    return runner(request)


def compare(observed: dict, expected: dict) -> list:
    """Every mismatch is a string; an empty list means the fixture passed."""
    problems = []

    for field in ("status", "writes"):
        if field in expected and observed[field] != expected[field]:
            problems.append(f"{field}: expected {expected[field]!r}, got {observed[field]!r}")

    if "unknown" in expected:
        want = sorted(
            (entry["path"], entry["reason"]) for entry in expected["unknown"]
        )
        got = sorted((entry["path"], entry["reason"]) for entry in observed["unknown"])
        if want != got:
            problems.append(f"unknown: expected {want}, got {got}")

    if "unknown_quartets_complete" in expected and expected["unknown_quartets_complete"]:
        for entry in observed["unknown"]:
            keys = set(entry)
            if keys != {"path", "raw", "reason", "source"}:
                problems.append(f"unknown quartet has wrong keys: {sorted(keys)}")

    if "rejected_fields" in expected:
        want = sorted(expected["rejected_fields"])
        got = sorted(entry["field"] for entry in observed["rejected"])
        if want != got:
            problems.append(f"rejected: expected {want}, got {got}")

    if "quarantined" in expected:
        want = sorted(expected["quarantined"])
        got = sorted(observed["quarantined"])
        if want != got:
            problems.append(f"quarantined: expected {want}, got {got}")

    if "candidates" in expected:
        want = sorted(expected["candidates"])
        got = sorted(observed["candidates"])
        if want != got:
            problems.append(f"candidates: expected {want}, got {got}")

    if "questions_max" in expected and len(observed["questions"]) > expected["questions_max"]:
        problems.append(
            f"questions: expected at most {expected['questions_max']}, got {len(observed['questions'])}"
        )

    if "artifact_present" in expected:
        present = observed["artifact"] is not None
        if present != expected["artifact_present"]:
            problems.append(
                f"artifact presence: expected {expected['artifact_present']}, got {present}"
            )

    for dotted, want in (expected.get("artifact_expect") or {}).items():
        try:
            got = dig(observed["artifact"], dotted)
        except (KeyError, IndexError, TypeError):
            problems.append(f"artifact.{dotted}: missing, expected {want!r}")
            continue
        if got != want:
            problems.append(f"artifact.{dotted}: expected {want!r}, got {got!r}")

    for dotted in expected.get("artifact_absent") or []:
        if not missing(observed["artifact"], dotted):
            problems.append(f"artifact.{dotted}: present, but must stay absent (no guessed value)")

    if "revision_is_sha256" in expected and expected["revision_is_sha256"]:
        revision = (observed["artifact"] or {}).get("revision", "")
        if not re.fullmatch(r"[0-9a-f]{64}", str(revision)):
            problems.append(f"revision is not a sha256: {revision!r}")

    return problems


def run_fixture(directory: pathlib.Path) -> dict:
    request_doc = load(directory / "input.json")
    expected = load(directory / "expected.json")
    stage = request_doc["stage"]
    observed = run_request(stage, request_doc["request"])
    return {
        "fixture_id": request_doc.get("fixture_id", directory.name),
        "stage": stage,
        "problems": compare(observed, expected),
        "observed": observed,
    }


def fixture_dirs(root: pathlib.Path) -> list:
    if (root / "input.json").is_file():
        return [root]
    return sorted(path.parent for path in root.rglob("input.json"))


def main(argv) -> int:
    if "--list-stages" in argv:
        print(json.dumps(sorted(ui_stages.STAGES), indent=2))
        return 0

    as_json = "--json" in argv
    recursive = "--recursive" in argv
    targets = [arg for arg in argv[1:] if not arg.startswith("--")]
    if not targets:
        print(__doc__)
        return 2

    root = pathlib.Path(targets[0])
    directories = fixture_dirs(root) if recursive else [root]
    reports = []
    failed = 0
    for directory in directories:
        report = run_fixture(directory)
        reports.append(report)
        if report["problems"]:
            failed += 1

    if as_json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
    else:
        for report in reports:
            mark = "FAIL" if report["problems"] else "ok"
            print(f"[{mark}] {report['fixture_id']} ({report['stage']}) -> {report['observed']['status']}")
            for problem in report["problems"]:
                print(f"       {problem}")
        print(f"\n{len(reports) - failed}/{len(reports)} fixtures matched")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
