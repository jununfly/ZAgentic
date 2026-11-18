#!/usr/bin/env python3
"""Consumer-side gate for a docs_governance.py report (issue #264 layer C).

The validator emits facts and gates only on mechanical ERRORs. This script is
the *consumer's* half: it reads the JSON report on stdin and applies the gate
criteria shipped in `references/gate-rules.json`. Signals pass by default; a
consumer opts in per signal with `--escalate CODE`. Signals marked never-gate
are rejected even if requested, because their evidence is not external to the
executing agent (P0 invariant).

    python3 docs_governance.py . --validate | \
      python3 check_gate.py --escalate EXEC_CHECKLIST_NOT_DECLARED

Exit 0 = pass, 1 = fail, 2 = bad input / bad rule file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_RULES = Path(__file__).resolve().parents[1] / "references" / "gate-rules.json"


def load_rules(path: Path) -> dict:
    """Load and lightly validate the gate criteria (closed shape, no silent
    fallback to hardcoded values if the file is missing or malformed)."""
    rules = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "error_codes", "error_prefixes", "escalatable_signals", "never_gate_signals",
    }
    missing = required - set(rules)
    if missing:
        raise ValueError(f"gate rules missing keys: {sorted(missing)}")
    overlap = set(rules["escalatable_signals"]) & set(rules["never_gate_signals"])
    if overlap:
        raise ValueError(f"gate rules classify codes as both escalatable and never-gate: {sorted(overlap)}")
    return rules


def decide(report: dict, rules: dict, escalations: set[str]) -> dict:
    """Apply the rules to a report. Pure — the CLI owns stdin/exit code."""
    diagnostics = report.get("diagnostics")
    if not isinstance(diagnostics, list):
        raise ValueError("report has no diagnostics list")

    error_codes = set(rules["error_codes"])
    prefixes = tuple(rules["error_prefixes"])
    escalatable = set(rules["escalatable_signals"])
    never_gate = set(rules["never_gate_signals"])

    reasons: list[str] = []
    seen: set[str] = set()
    for item in diagnostics:
        code = item.get("code", "") if isinstance(item, dict) else ""
        if code in seen:
            continue
        seen.add(code)
        if code in error_codes or code.startswith(prefixes):
            reasons.append(code)
        elif code in escalatable and code in escalations:
            reasons.append(code)

    rejected = sorted(code for code in escalations if code in never_gate or code not in escalatable)
    checklist = report.get("checklist")
    return {
        "verdict": "fail" if reasons else "pass",
        "reasons": sorted(reasons),
        "rejected_escalations": rejected,
        "checklist_status": checklist.get("status") if isinstance(checklist, dict) else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES,
        help=f"gate criteria JSON (default: {DEFAULT_RULES})",
    )
    parser.add_argument(
        "--escalate",
        action="append",
        default=[],
        metavar="CODE",
        help="signal code to gate on (repeatable); never-gate codes are rejected",
    )
    args = parser.parse_args()
    try:
        rules = load_rules(args.rules)
        report = json.loads(sys.stdin.read())
        result = decide(report, rules, set(args.escalate))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": "GATE_INPUT_ERROR", "message": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["verdict"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
