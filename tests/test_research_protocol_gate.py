#!/usr/bin/env python3
"""TDD regression for issue #243's CI coverage deviation.

Seams under test (confirmed before any test was written):
  S1 governance     -- .github/workflows/research-compiler-contract.yml: which
                       contracts an unconditional (no `if`) CI job runs.
  S2 publisher CLI  -- publish_report.py's observable artefacts, receipt and
                       exit code, exercised through verify_technical_report.py.
  S3 compiler seam  -- the stdin/stdout JSON protocol boundary implemented by
                       the injected test double.

Slices are added one at a time, red first. Expected values are independent
literals from the protocol/governance contract, never recomputed from the code
under test.
"""

import json
import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github/workflows/research-compiler-contract.yml"


def workflow_jobs():
    """Read the workflow at its public configuration boundary."""

    import yaml  # hard dependency: a missing PyYAML must fail, never skip

    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def unconditional_run_commands():
    return [
        step.get("run", "")
        for job in workflow_jobs().values()
        if "if" not in job
        for step in job.get("steps", [])
    ]


class TestUnconditionalCoverage(unittest.TestCase):
    def test_publisher_quality_gate_contract_runs_without_an_if_guard(self):
        """The publisher gate belongs to ZAgentic, so CI must always run it."""

        self.assertTrue(
            any("verify_technical_report.py" in command for command in unconditional_run_commands()),
            "publisher quality-gate contract is not covered by an unconditional CI job",
        )


DOUBLE = REPO_ROOT / "tests/fixtures/zj_research_protocol_double.py"


def describe(protocol):
    return subprocess.run(
        [sys.executable, str(DOUBLE)],
        input=json.dumps({"protocol": protocol, "operation": "describe"}),
        capture_output=True,
        text=True,
    )


class TestProtocolDoubleBoundary(unittest.TestCase):
    """S3: the injected double must speak both protocols at the CLI seam."""

    def test_describe_reports_all_required_research_operations(self):
        completed = describe("zj-research-cli/v1")
        self.assertEqual(0, completed.returncode, msg=completed.stderr)
        self.assertEqual(
            {"collect", "compile-report", "render-html", "evaluate"},
            set(json.loads(completed.stdout)["result"]["operations"]),
        )

    def test_describe_reports_all_required_evaluation_operations(self):
        completed = describe("zj-research-eval-cli/v1")
        self.assertEqual(0, completed.returncode, msg=completed.stderr)
        self.assertEqual(
            {"validate-assets", "calibrate-judge"},
            set(json.loads(completed.stdout)["result"]["operations"]),
        )


class TestHandshakeCoverage(unittest.TestCase):
    """S1: the handshake must stay in the unconditional CI job."""

    def test_unconditional_job_runs_both_adapter_handshakes(self):
        self.assertTrue(
            any(
                "research_cli.py --check" in command and "research_eval_cli.py --check" in command
                for command in unconditional_run_commands()
            ),
            "adapter describe handshake is not covered by an unconditional CI job",
        )


if __name__ == "__main__":
    unittest.main()
