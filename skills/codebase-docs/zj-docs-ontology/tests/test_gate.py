#!/usr/bin/env python3
"""Regression tests for the consumer-side gate (issue #264 platform layer C).

The tool emits facts; a *consumer* decides which facts to gate on. The gate
rules ship inside the skill and travel with it to any target repository. This
module pins three things: the rules agree with the tool's own allowlists,
escalation is opt-in by the consumer, and signals that must never gate cannot
be escalated even if a consumer asks.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
REFERENCES = SKILL_ROOT / "references"
RULES = REFERENCES / "gate-rules.json"
GATE_SCRIPT = SCRIPTS / "check_gate.py"
TOOL_SCRIPT = SCRIPTS / "docs_governance.py"

SPEC_GATE = importlib.util.spec_from_file_location("check_gate", GATE_SCRIPT)
assert SPEC_GATE and SPEC_GATE.loader
GATE = importlib.util.module_from_spec(SPEC_GATE)
sys.modules[SPEC_GATE.name] = GATE
SPEC_GATE.loader.exec_module(GATE)

SPEC_TOOL = importlib.util.spec_from_file_location("docs_governance_gate", TOOL_SCRIPT)
assert SPEC_TOOL and SPEC_TOOL.loader
TOOL = importlib.util.module_from_spec(SPEC_TOOL)
sys.modules[SPEC_TOOL.name] = TOOL
SPEC_TOOL.loader.exec_module(TOOL)


def report_with(codes: list[str], *, checklist_status: str = "checked") -> dict:
    return {
        "diagnostics": [{"code": c, "path": "", "message": c} for c in codes],
        "checklist": {"topic": "a-topic", "status": checklist_status},
    }


class RuleConsistencyTest(unittest.TestCase):
    """The rule file is a second copy of a fact — it must stay locked to the
    tool's allowlists or the gate silently drifts from what the tool can emit."""

    def setUp(self) -> None:
        self.rules = GATE.load_rules(RULES)

    def test_every_tool_error_code_is_a_gate_in_the_rules(self) -> None:
        self.assertEqual(TOOL.ERROR_CODES, frozenset(self.rules["error_codes"]))

    def test_tool_error_prefixes_match_the_rules(self) -> None:
        self.assertEqual(frozenset(TOOL.ERROR_PREFIXES), frozenset(self.rules["error_prefixes"]))

    def test_never_gate_signals_cover_all_tool_signals(self) -> None:
        # A signal is either consumer-escalatable or never-gate, never unlisted.
        escalatable = set(self.rules["escalatable_signals"])
        never = set(self.rules["never_gate_signals"])
        self.assertEqual(TOOL.SIGNAL_CODES, escalatable | never)
        self.assertEqual(set(), escalatable & never)

    def test_the_new_bare_validate_signal_is_escalatable(self) -> None:
        self.assertIn("EXEC_CHECKLIST_NOT_DECLARED", self.rules["escalatable_signals"])

    def test_fingerprint_signal_is_never_gate(self) -> None:
        self.assertIn("EXEC_STEP5_FINGERPRINT_MISMATCH", self.rules["never_gate_signals"])


class DecideTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = GATE.load_rules(RULES)

    def decide(self, report: dict, escalations: set[str] | None = None) -> dict:
        return GATE.decide(report, self.rules, escalations or set())

    def test_error_code_gates_without_escalation(self) -> None:
        result = self.decide(report_with(["UNDECLARED_RETIREMENT"]))
        self.assertEqual("fail", result["verdict"])
        self.assertIn("UNDECLARED_RETIREMENT", result["reasons"])

    def test_error_prefix_gates(self) -> None:
        result = self.decide(report_with(["MAP_LINK_BROKEN"]))
        self.assertEqual("fail", result["verdict"])

    def test_signal_passes_by_default(self) -> None:
        result = self.decide(report_with(["EXEC_CHECKLIST_NOT_DECLARED"]))
        self.assertEqual("pass", result["verdict"])

    def test_escalated_signal_gates(self) -> None:
        result = self.decide(
            report_with(["EXEC_CHECKLIST_NOT_DECLARED"]),
            {"EXEC_CHECKLIST_NOT_DECLARED"},
        )
        self.assertEqual("fail", result["verdict"])
        self.assertIn("EXEC_CHECKLIST_NOT_DECLARED", result["reasons"])

    def test_never_gate_signal_rejects_escalation(self) -> None:
        """Even if a consumer asks, a self-certification signal cannot gate."""
        result = self.decide(
            report_with(["EXEC_STEP5_FINGERPRINT_MISMATCH"]),
            {"EXEC_STEP5_FINGERPRINT_MISMATCH"},
        )
        self.assertEqual("pass", result["verdict"])
        self.assertIn("rejected_escalations", result)
        self.assertIn("EXEC_STEP5_FINGERPRINT_MISMATCH", result["rejected_escalations"])

    def test_unknown_escalation_code_is_rejected_not_ignored(self) -> None:
        result = self.decide(report_with([]), {"TOTALLY_MADE_UP"})
        self.assertIn("TOTALLY_MADE_UP", result["rejected_escalations"])

    def test_clean_report_passes(self) -> None:
        self.assertEqual("pass", self.decide(report_with([]))["verdict"])

    def test_checklist_not_declared_status_is_visible(self) -> None:
        result = self.decide(report_with([], checklist_status="not-declared"))
        self.assertEqual("not-declared", result["checklist_status"])


class GateCommandLineTest(unittest.TestCase):
    def run_gate(self, report: dict, *args: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(GATE_SCRIPT), *args],
            input=json.dumps(report), capture_output=True, text=True,
        )
        return proc.returncode, json.loads(proc.stdout)

    def test_error_report_exits_nonzero(self) -> None:
        code, payload = self.run_gate(report_with(["UNCONFIRMED_MUTATION"]))
        self.assertNotEqual(0, code)
        self.assertEqual("fail", payload["verdict"])

    def test_signal_report_exits_zero_by_default(self) -> None:
        code, _ = self.run_gate(report_with(["EXEC_CHECKLIST_NOT_DECLARED"]))
        self.assertEqual(0, code)

    def test_escalation_flag_gates_the_signal(self) -> None:
        code, payload = self.run_gate(
            report_with(["EXEC_CHECKLIST_NOT_DECLARED"]),
            "--escalate", "EXEC_CHECKLIST_NOT_DECLARED",
        )
        self.assertNotEqual(0, code)
        self.assertEqual("fail", payload["verdict"])

    def test_never_gate_flag_exits_zero_even_when_requested(self) -> None:
        code, payload = self.run_gate(
            report_with(["EXEC_STEP5_FINGERPRINT_MISMATCH"]),
            "--escalate", "EXEC_STEP5_FINGERPRINT_MISMATCH",
        )
        self.assertEqual(0, code)
        self.assertIn("EXEC_STEP5_FINGERPRINT_MISMATCH", payload["rejected_escalations"])

    def test_report_from_stdin_is_parsed(self) -> None:
        """CI pipes the validator's JSON straight in — no intermediate file."""
        code, payload = self.run_gate({"diagnostics": [], "checklist": {"status": "checked", "topic": "t"}})
        self.assertEqual(0, code)
        self.assertEqual("pass", payload["verdict"])


if __name__ == "__main__":
    unittest.main()
