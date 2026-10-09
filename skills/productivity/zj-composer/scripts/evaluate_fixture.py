#!/usr/bin/env python3
"""Evaluate a deterministic Composer fixture and its scenario oracle.

The evaluator is intentionally local and artifact based.  It composes the
generic Plan validator with a small JSON oracle; it never contacts an external
repository and never executes a capability named by the Plan.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_plan import field_value, parse_sections, validate_plan  # noqa: E402


RESULT_SCHEMA = "zj-composer/fixture-result/v1"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def oracle_error(category: str, message: str, step: Optional[int] = None) -> dict[str, Any]:
    value: dict[str, Any] = {"category": category, "message": message}
    if step is not None:
        value["step"] = step
    return value


def evaluate_oracle(
    fixture: dict[str, Any],
    oracle: dict[str, Any],
    sections: dict[str, dict[str, Any]],
    lines: list[str],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    fixture_id = fixture.get("fixture_id")
    if oracle.get("fixture_id") != fixture_id:
        errors.append(oracle_error("fixture_identity_mismatch", "oracle fixture_id does not match input fixture_id"))

    identity = sections.get("Identity", {})
    plan_id, _ = field_value(identity, "plan_id")
    status, _ = field_value(identity, "status")
    if plan_id != fixture.get("expected_plan_id"):
        errors.append(oracle_error("plan_identity_mismatch", "Plan id does not match the frozen fixture input"))
    if status != oracle.get("expected_status"):
        errors.append(oracle_error("plan_status_mismatch", "Plan status does not match the fixture oracle"))

    intent_text = "\n".join(value for value, _ in sections.get("Intent", {}).get("fields", {}).values())
    for keyword in oracle.get("required_intent_keywords", []):
        if str(keyword).casefold() not in intent_text.casefold():
            errors.append(oracle_error("intent_oracle_mismatch", f"Intent is missing required keyword: {keyword}"))

    provenance_text = "\n".join(value for value, _ in sections.get("Evidence and provenance", {}).get("fields", {}).values())
    snapshot_id, _ = field_value(sections.get("Evidence and provenance", {}), "skill_index_snapshot")
    if snapshot_id.strip("`") != fixture.get("snapshot_id"):
        errors.append(oracle_error("snapshot_identity_mismatch", "Plan snapshot id does not match the frozen fixture input"))
    for reference in oracle.get("required_provenance_references", []):
        if str(reference).casefold() not in provenance_text.casefold():
            errors.append(oracle_error("provenance_oracle_mismatch", f"Provenance is missing required reference: {reference}"))

    permission_boundary, _ = field_value(sections.get("Intent", {}), "permission_boundary")
    for keyword in oracle.get("required_permission_keywords", []):
        if str(keyword).casefold() not in permission_boundary.casefold():
            errors.append(oracle_error("permission_oracle_mismatch", f"Permission boundary is missing: {keyword}"))

    for expected_line in oracle.get("required_gap_lines", []):
        if not any(line.strip() == str(expected_line) for line in lines):
            errors.append(oracle_error("gap_oracle_mismatch", f"Plan is missing exact gap line: {expected_line}"))

    for section_name, keywords in oracle.get("required_section_keywords", {}).items():
        section_text = "\n".join(
            value for value, _ in sections.get(section_name, {}).get("fields", {}).values()
        )
        for keyword in keywords:
            if str(keyword).casefold() not in section_text.casefold():
                errors.append(oracle_error("section_oracle_mismatch", f"{section_name} is missing keyword: {keyword}"))

    steps = sections.get("Capability composition", {}).get("steps", [])
    expected_steps = oracle.get("expected_steps", [])
    if len(steps) != len(expected_steps):
        errors.append(oracle_error("step_count_mismatch", f"Expected {len(expected_steps)} capability steps, found {len(steps)}"))

    for index, expected in enumerate(expected_steps):
        if index >= len(steps):
            break
        step = steps[index]
        number = step.get("number")
        if number != expected.get("number"):
            errors.append(oracle_error("step_number_mismatch", f"Expected Step {expected.get('number')}, found Step {number}", number))
        fields = step.get("fields", {})
        skill, _ = fields.get("skill_or_workflow", ("", None))
        if skill != expected.get("skill_or_workflow"):
            errors.append(oracle_error("capability_order_mismatch", f"Expected {expected.get('skill_or_workflow')}, found {skill}", number))
        reason, _ = fields.get("reason", ("", None))
        for keyword in expected.get("reason_keywords", []):
            if str(keyword).casefold() not in reason.casefold():
                errors.append(oracle_error("selection_reason_mismatch", f"Step {number} reason is missing keyword: {keyword}", number))
        outputs, _ = fields.get("outputs", ("", None))
        for keyword in expected.get("required_output_keywords", []):
            if str(keyword).casefold() not in outputs.casefold():
                errors.append(oracle_error("step_output_mismatch", f"Step {number} outputs are missing keyword: {keyword}", number))
        dependencies, _ = fields.get("dependencies", ("", None))
        if number == 1:
            if dependencies.casefold() not in {"none", "none declared", "no dependencies"}:
                errors.append(oracle_error("dependency_oracle_mismatch", "Step 1 must declare no dependency", number))
        elif f"step {number - 1}" not in dependencies.casefold():
            errors.append(oracle_error("dependency_oracle_mismatch", f"Step {number} must depend on Step {number - 1}", number))

    capability_text = "\n".join(
        value
        for step in steps
        for value, _ in step.get("fields", {}).values()
    )
    for term in oracle.get("forbidden_capability_terms", []):
        if str(term).casefold() in capability_text.casefold():
            errors.append(oracle_error("forbidden_capability", f"Capability composition contains forbidden term: {term}"))

    return sorted(errors, key=lambda item: (item.get("category", ""), item.get("step", 0), item["message"]))


def evaluate_fixture(fixture_dir: Path, root: Path) -> dict[str, Any]:
    fixture = read_json(fixture_dir / "input.json")
    oracle = read_json(fixture_dir / "oracle.json")
    plan_path = fixture_dir / str(oracle.get("plan_filename", "plan.md"))
    validation = validate_plan(plan_path.resolve(), root, None)
    try:
        validation["plan"]["path"] = plan_path.resolve().relative_to(root).as_posix()
    except ValueError:
        validation["plan"]["path"] = plan_path.name

    try:
        text = plan_path.read_text(encoding="utf-8")
        sections, _ = parse_sections(text.splitlines(), [])
        oracle_errors = evaluate_oracle(fixture, oracle, sections, text.splitlines())
    except (OSError, UnicodeError) as exc:
        oracle_errors = [oracle_error("fixture_read_error", str(exc))]

    result = {
        "schema": RESULT_SCHEMA,
        "fixture_id": fixture.get("fixture_id"),
        "plan_id": validation.get("plan", {}).get("plan_id"),
        "template_version": validation.get("plan", {}).get("template_version"),
        "source_revision": fixture.get(
            "source_revision",
            fixture.get("repository", {}).get("revision", fixture.get("snapshot_id")),
        ),
        "valid": bool(validation.get("valid")) and not oracle_errors,
        "validation": validation,
        "oracle": {
            "valid": not oracle_errors,
            "errors": oracle_errors,
        },
    }
    return result


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a deterministic Composer fixture.")
    parser.add_argument("fixture_dir", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--output", type=Path)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    result = evaluate_fixture(args.fixture_dir.resolve(), args.root.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
