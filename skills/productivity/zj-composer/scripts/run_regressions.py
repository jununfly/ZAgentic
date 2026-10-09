#!/usr/bin/env python3
"""Run local, deterministic regression checks for Composer Plan artifacts.

The runner exercises the validator at the Markdown boundary.  Every negative
case is written to a temporary copy of a known-good fixture, so the checked-in
Plans are never mutated.  It does not invoke a Plan capability, open a
network connection, run Git, or perform a handoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_fixture import evaluate_fixture  # noqa: E402
from validate_plan import field_value, parse_sections, validate_plan  # noqa: E402


RESULT_SCHEMA = "zj-composer/regression-result/v1"
SNAPSHOT_DIGEST_RE = re.compile(r"(\*\*catalog_revision_or_digest:\*\*\s*`)([^`]+)(`)")


class RegressionError(RuntimeError):
    """A controlled regression case could not be constructed or checked."""


class EffectLedger:
    """Counts side effects that the runner is allowed to perform."""

    def __init__(self) -> None:
        self.temporary_writes = 0
        self.result_writes = 0
        self.network_calls = 0
        self.git_publications = 0
        self.credential_reads = 0
        self.irreversible_actions = 0

    def write_temporary(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.temporary_writes += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "declared": {
                "temporary_fixture_copies": self.temporary_writes,
                "regression_result": self.result_writes,
            },
            "network_calls": self.network_calls,
            "git_publications": self.git_publications,
            "credential_reads": self.credential_reads,
            "irreversible_actions": self.irreversible_actions,
            "unapproved_side_effects": 0,
            "safe": all(
                value == 0
                for value in (
                    self.network_calls,
                    self.git_publications,
                    self.credential_reads,
                    self.irreversible_actions,
                )
            ),
        }


@contextmanager
def side_effect_guards(ledger: EffectLedger) -> Iterator[None]:
    """Fail closed if this local-only runner attempts network or subprocess use."""

    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection
    original_subprocess: dict[str, Any] = {
        name: getattr(subprocess, name)
        for name in ("run", "Popen", "call", "check_call", "check_output")
    }

    def blocked_network(*_args: Any, **_kwargs: Any) -> None:
        ledger.network_calls += 1
        raise RegressionError("network access is forbidden during Composer regressions")

    def blocked_process(*_args: Any, **_kwargs: Any) -> None:
        ledger.git_publications += 1
        raise RegressionError("subprocess/Git publication is forbidden during Composer regressions")

    socket.socket.connect = blocked_network  # type: ignore[assignment]
    socket.create_connection = blocked_network  # type: ignore[assignment]
    for name in original_subprocess:
        setattr(subprocess, name, blocked_process)
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]
        for name, function in original_subprocess.items():
            setattr(subprocess, name, function)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_files(fixture_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(fixture_dir).as_posix(): sha256(path)
        for path in sorted(fixture_dir.rglob("*"))
        if path.is_file()
    }


def preserve_newline(original: str, lines: list[str]) -> str:
    value = "\n".join(lines)
    return value + ("\n" if original.endswith("\n") else "")


def replace_field(
    text: str,
    section_name: str,
    field_name: str,
    replacement: str,
    *,
    step_number: Optional[int] = None,
) -> str:
    """Replace one Markdown field while staying inside the named section/step."""

    lines = text.splitlines()
    in_section = False
    active_step: Optional[int] = None
    prefix = f"- **{field_name}:**"
    for index, line in enumerate(lines):
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            in_section = heading.group(1).strip() == section_name
            active_step = None
            continue
        if not in_section:
            continue
        step = re.match(r"^###\s+Step\s+(\d+)\s+[-—]", line, re.IGNORECASE)
        if step:
            active_step = int(step.group(1))
            continue
        if not line.lstrip().startswith(prefix):
            continue
        if step_number is not None and active_step != step_number:
            continue
        lines[index] = f"- **{field_name}:** {replacement}"
        return preserve_newline(text, lines)
    qualifier = f" in Step {step_number}" if step_number is not None else ""
    raise RegressionError(f"field {section_name}.{field_name}{qualifier} not found")


def append_field(
    text: str,
    section_name: str,
    field_name: str,
    suffix: str,
    *,
    step_number: Optional[int] = None,
) -> str:
    lines = text.splitlines()
    in_section = False
    active_step: Optional[int] = None
    prefix = f"- **{field_name}:**"
    for index, line in enumerate(lines):
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            in_section = heading.group(1).strip() == section_name
            active_step = None
            continue
        if not in_section:
            continue
        step = re.match(r"^###\s+Step\s+(\d+)\s+[-—]", line, re.IGNORECASE)
        if step:
            active_step = int(step.group(1))
            continue
        if not line.lstrip().startswith(prefix):
            continue
        if step_number is not None and active_step != step_number:
            continue
        lines[index] = f"{line}{suffix}"
        return preserve_newline(text, lines)
    qualifier = f" in Step {step_number}" if step_number is not None else ""
    raise RegressionError(f"field {section_name}.{field_name}{qualifier} not found")


def mutate_gap(text: str) -> str:
    if "required skill：" in text:
        return text.replace("required skill：", "required skill:", 1)
    # The research fixture has no unresolved gap by design.  Turn its explicit
    # no-gap statement into the malformed ASCII form so both positive fixtures
    # exercise the same validator category.
    marker = "No unresolved capability gaps."
    if marker in text:
        return text.replace(marker, "required skill: missing capability", 1)
    raise RegressionError("fixture does not contain a gap marker or explicit no-gap statement")


def mutate_snapshot_digest(text: str) -> str:
    match = SNAPSHOT_DIGEST_RE.search(text)
    if not match:
        raise RegressionError("catalog_revision_or_digest field not found")
    return text[: match.start(2)] + ("0" * len(match.group(2))) + text[match.end(2) :]


def mutate_rejection(text: str) -> str:
    value = replace_field(text, "Identity", "status", "`rejected`")
    return replace_field(value, "Identity", "human_review", "`rejected`")


def case_definitions() -> list[dict[str, Any]]:
    return [
        {
            "id": "malformed-unicode-gap",
            "description": "Reject an ASCII colon where the exact full-width gap marker is required.",
            "expected_category": "malformed_gap",
            "mutate": mutate_gap,
        },
        {
            "id": "missing-prerequisite",
            "description": "Reject a prerequisite declaration that explicitly remains unresolved.",
            "expected_category": "unresolved_prerequisite",
            "mutate": lambda text: replace_field(
                text,
                "Capability composition",
                "prerequisites",
                "missing prerequisite evidence",
                step_number=1,
            ),
        },
        {
            "id": "stale-snapshot-digest",
            "description": "Reject a Plan whose catalog digest no longer matches the frozen snapshot.",
            "expected_category": "provenance_digest_mismatch",
            "mutate": mutate_snapshot_digest,
        },
        {
            "id": "authority-bypass",
            "description": "Reject authority text that bypasses Human approval.",
            "expected_category": "authority_bypass",
            "mutate": lambda text: replace_field(
                text,
                "Handoff",
                "authority_statement",
                "Composer bypasses Human authority and may continue automatically.",
            ),
        },
        {
            "id": "secret-shaped-output",
            "description": "Reject a secret-shaped literal inserted into a capability output.",
            "expected_category": "secret-shaped-output",
            "mutate": lambda text: append_field(
                text,
                "Capability composition",
                "outputs",
                " api_key=not-a-real-secret",
                step_number=1,
            ),
        },
        {
            "id": "unapproved-write",
            "description": "Reject a permission boundary that permits a production write without a gate.",
            "expected_category": "unapproved_side_effect",
            "mutate": lambda text: replace_field(
                text,
                "Intent",
                "permission_boundary",
                "Write production files.",
            ),
        },
        {
            "id": "conflicting-alternatives",
            "description": "Reject retained alternatives until a Human makes the explicit choice.",
            "expected_category": "unresolved_conflict",
            "mutate": lambda text: replace_field(
                text,
                "Capability composition",
                "excluded_alternatives",
                "CONFLICT: Human choice required between option A and option B.",
                step_number=1,
            ),
        },
    ]


def diagnostic_categories(validation: dict[str, Any]) -> list[str]:
    return sorted({item.get("category") for item in validation.get("diagnostics", []) if item.get("category")})


def inspect_handoff(plan_path: Path) -> dict[str, Any]:
    """Check the textual handoff contract without dispatching anything."""

    text = plan_path.read_text(encoding="utf-8")
    sections, _ = parse_sections(text.splitlines(), [])
    handoff = sections.get("Handoff", {})
    authority, _ = field_value(handoff, "authority_statement")
    preconditions, _ = field_value(handoff, "handoff_preconditions")
    authority_text = (authority or "").casefold()
    precondition_text = (preconditions or "").casefold()
    authority_ok = bool(
        re.search(r"composer.{0,60}(?:no|without).{0,30}(?:execution|authority)", authority_text)
        or "无执行权" in authority_text
    )
    preconditions_ok = (
        "human approval" in precondition_text
        and "passing plan validation" in precondition_text
        and ("oracle" in precondition_text or "fixture" in precondition_text)
    )
    return {
        "authority_statement_present": bool(authority),
        "authority_preserves_no_execution_authority": authority_ok,
        "handoff_preconditions_present": bool(preconditions),
        "handoff_preconditions_guarded": preconditions_ok,
        "passed": authority_ok and preconditions_ok,
    }


def run_negative_case(
    fixture_id: str,
    plan_text: str,
    case: dict[str, Any],
    temp_root: Path,
    ledger: EffectLedger,
) -> dict[str, Any]:
    case_dir = temp_root / fixture_id / str(case["id"])
    plan_path = case_dir / "plan.md"
    try:
        mutated = case["mutate"](plan_text)
        if mutated == plan_text:
            raise RegressionError("mutation did not change the Plan")
        ledger.write_temporary(plan_path, mutated)
        validation = validate_plan(plan_path, ROOT, None)
        categories = diagnostic_categories(validation)
        expected = str(case["expected_category"])
        passed = not validation.get("valid", True) and expected in categories
        return {
            "id": case["id"],
            "description": case["description"],
            "expected_category": expected,
            "observed_categories": categories,
            "validator_valid": bool(validation.get("valid")),
            "passed": passed,
        }
    except Exception as exc:  # keep all cases visible in the result
        return {
            "id": case["id"],
            "description": case["description"],
            "expected_category": case["expected_category"],
            "observed_categories": [],
            "validator_valid": None,
            "passed": False,
            "error": str(exc),
        }


def run_rejected_case(
    fixture_id: str,
    plan_text: str,
    temp_root: Path,
    ledger: EffectLedger,
) -> dict[str, Any]:
    case_dir = temp_root / fixture_id / "rejected-plan"
    plan_path = case_dir / "plan.md"
    try:
        rejected_text = mutate_rejection(plan_text)
        ledger.write_temporary(plan_path, rejected_text)
        validation = validate_plan(plan_path, ROOT, None)
        sections, _ = parse_sections(rejected_text.splitlines(), [])
        identity = sections.get("Identity", {})
        status, _ = field_value(identity, "status")
        review, _ = field_value(identity, "human_review")
        preserved = plan_path.is_file() and plan_path.read_text(encoding="utf-8") == rejected_text
        handoff_eligible = bool(validation.get("valid")) and status == "approved" and review == "approved"
        passed = (
            bool(validation.get("valid"))
            and status == "rejected"
            and review == "rejected"
            and preserved
            and not handoff_eligible
        )
        return {
            "id": "rejected-plan",
            "expected": {
                "status": "rejected",
                "human_review": "rejected",
                "preserved": True,
                "handoff_eligible": False,
            },
            "observed": {
                "validator_valid": bool(validation.get("valid")),
                "status": status,
                "human_review": review,
                "preserved": preserved,
                "handoff_eligible": handoff_eligible,
            },
            "passed": passed,
        }
    except Exception as exc:
        return {
            "id": "rejected-plan",
            "expected": {
                "status": "rejected",
                "human_review": "rejected",
                "preserved": True,
                "handoff_eligible": False,
            },
            "observed": {},
            "passed": False,
            "error": str(exc),
        }


def run_removal_simulation(
    root: Path,
    temp_root: Path,
    plan_text: str,
    ledger: EffectLedger,
) -> dict[str, Any]:
    simulation = temp_root / "removal-simulation"
    experimental = simulation / "composer-experiment" / "skills" / "productivity" / "zj-composer"
    historical = simulation / "historical-artifacts" / "composer-v0-plan.md"
    original_path = simulation / "original-capability" / "skills" / "engineering" / "zj-leader" / "SKILL.md"
    composer_source = root / "skills" / "productivity" / "zj-composer" / "SKILL.md"
    original_source = root / "skills" / "engineering" / "zj-leader" / "SKILL.md"
    ledger.write_temporary(experimental / "SKILL.md", composer_source.read_text(encoding="utf-8"))
    ledger.write_temporary(historical, plan_text)
    ledger.write_temporary(original_path, original_source.read_text(encoding="utf-8"))
    shutil.rmtree(simulation / "composer-experiment")
    return {
        "passed": not experimental.exists() and historical.is_file() and original_path.is_file(),
        "experimental_layer_removed": not experimental.exists(),
        "historical_artifact_preserved": historical.is_file(),
        "original_capability_path_preserved": original_path.is_file(),
        "real_repository_touched": False,
    }


def run_regressions(root: Path, output: Path) -> dict[str, Any]:
    global ROOT
    ROOT = root.resolve()
    ledger = EffectLedger()
    fixture_root = ROOT / "skills-outputs" / "zj-composer"
    fixture_dirs = [
        fixture_root / "external-repository-research",
        fixture_root / "tool-combination-design",
    ]
    before = {path.name: fixture_files(path) for path in fixture_dirs}
    source_paths = [
        ROOT / "skills/productivity/zj-composer/SKILL.md",
        ROOT / "skills/productivity/zj-composer/scripts/validate_plan.py",
        ROOT / "skills/productivity/zj-composer/scripts/evaluate_fixture.py",
        ROOT / "docs/plans/roadmap-zj-composer.json",
    ]
    # Include every path pinned by the active catalog snapshot in the integrity
    # check.  This catches an accidental mutation of a source file even when a
    # fixture Plan itself remains unchanged.
    for fixture_dir in fixture_dirs:
        fixture_input = json.loads((fixture_dir / "input.json").read_text(encoding="utf-8"))
        snapshot_id = fixture_input.get("snapshot_id")
        snapshot_path = fixture_root / "catalog-snapshots" / f"{snapshot_id}.json"
        source_paths.append(snapshot_path)
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        for item in snapshot.get("source", {}).get("files", []):
            relative = item.get("path") if isinstance(item, dict) else None
            if isinstance(relative, str):
                source_paths.append(ROOT / relative)
    source_paths = list(dict.fromkeys(source_paths))
    source_before = {path.as_posix(): sha256(path) for path in source_paths}
    fixtures_result: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="zj-composer-regression-") as temp_name:
        temp_root = Path(temp_name)
        with side_effect_guards(ledger):
            for fixture_dir in fixture_dirs:
                fixture_id = fixture_dir.name
                fixture_eval = evaluate_fixture(fixture_dir, ROOT)
                plan_path = fixture_dir / "plan.md"
                plan_text = plan_path.read_text(encoding="utf-8")
                handoff = inspect_handoff(plan_path)
                negative_cases = [
                    run_negative_case(fixture_id, plan_text, case, temp_root, ledger)
                    for case in case_definitions()
                ]
                rejected = run_rejected_case(fixture_id, plan_text, temp_root, ledger)
                fixtures_result.append(
                    {
                        "fixture_id": fixture_id,
                        "positive": {
                            "valid": bool(fixture_eval.get("valid")),
                            "validator_valid": bool(fixture_eval.get("validation", {}).get("valid")),
                            "oracle_valid": bool(fixture_eval.get("oracle", {}).get("valid")),
                            "errors": fixture_eval.get("validation", {}).get("summary", {}).get("errors"),
                            "warnings": fixture_eval.get("validation", {}).get("summary", {}).get("warnings"),
                        },
                        "handoff_contract": handoff,
                        "negative_cases": negative_cases,
                        "rejected_plan": rejected,
                    }
                )
            removal = run_removal_simulation(ROOT, temp_root, (fixture_dirs[0] / "plan.md").read_text(encoding="utf-8"), ledger)
    temporary_directory_removed = not temp_root.exists()

    after = {path.name: fixture_files(path) for path in fixture_dirs}
    source_after = {path.as_posix(): sha256(path) for path in source_paths}
    fixture_integrity = before == after
    source_integrity = source_before == source_after
    path_integrity = all(
        fixture_root.joinpath(fixture_id, "plan.md").is_file()
        for fixture_id in ("external-repository-research", "tool-combination-design")
    )
    negative_passed = all(
        case["passed"]
        for fixture in fixtures_result
        for case in fixture["negative_cases"]
    )
    rejected_passed = all(fixture["rejected_plan"]["passed"] for fixture in fixtures_result)
    handoff_passed = all(fixture["handoff_contract"]["passed"] for fixture in fixtures_result)
    positive_passed = all(
        fixture["positive"]["valid"]
        and fixture["positive"]["validator_valid"]
        and fixture["positive"]["oracle_valid"]
        and fixture["positive"]["errors"] == 0
        and fixture["positive"]["warnings"] == 0
        for fixture in fixtures_result
    )
    result = {
        "schema": RESULT_SCHEMA,
        "fixtures": fixtures_result,
        "checks": {
            "positive_fixtures_pass": positive_passed,
            "negative_categories_pass": negative_passed,
            "rejected_plans_preserved_and_not_handoffable": rejected_passed,
            "source_integrity": source_integrity,
            "fixture_path_integrity": path_integrity and fixture_integrity,
            "authority_and_handoff_guarded": handoff_passed and rejected_passed,
            "removal_simulation": removal,
            "temporary_directory_removed": temporary_directory_removed,
        },
        "side_effects": ledger.as_dict(),
    }
    # The caller writes exactly one declared result artifact after this
    # function returns; include that approved write in the ledger before the
    # result is serialized.
    result["side_effects"]["declared"]["regression_result"] = 1
    result["valid"] = bool(
        positive_passed
        and negative_passed
        and rejected_passed
        and handoff_passed
        and source_integrity
        and fixture_integrity
        and path_integrity
        and removal["passed"]
        and temporary_directory_removed
        and ledger.as_dict()["safe"]
    )
    return result


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Composer negative, safety, handoff, and removal regressions.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[4] / "skills-outputs/zj-composer/regression/regression-result.json",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    output = args.output.resolve()
    result = run_regressions(root, output)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
