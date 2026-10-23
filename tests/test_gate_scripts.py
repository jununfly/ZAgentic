#!/usr/bin/env python3
"""TDD regression for F4: gate scripts must (1) run from any cwd, and
(2) fail loudly when a unittest suite collects nothing.

Seam under test (S2 — gate process boundary):
  - scripts/assert_unittest_result.py exit code semantics
  - scripts/run_zj_discuss_gate.sh and scripts/run_ui_skills_gate.sh both exit 0
    when invoked from a directory outside the repository.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = REPO_ROOT / "scripts" / "assert_unittest_result.py"
DISCUSS_GATE = REPO_ROOT / "scripts" / "run_zj_discuss_gate.sh"
UI_GATE = REPO_ROOT / "scripts" / "run_ui_skills_gate.sh"


class TestAssertUnittestResult(unittest.TestCase):
    def _case(self, text, expected_rc):
        p = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False)
        p.write(text)
        p.close()
        rc = subprocess.run(
            [sys.executable, str(HELPER), p.name, "unit"],
            capture_output=True, text=True,
        ).returncode
        self.assertEqual(rc, expected_rc, msg=repr(text))

    def test_zero_collection_fails(self):
        self._case("Ran 0 tests in 0.001s\n\nOK\n", 1)

    def test_pass_ok(self):
        self._case("Ran 5 tests in 0.010s\n\nOK\n", 0)

    def test_failure_fails(self):
        self._case("Ran 3 tests\nFAILED (failures=1)\n", 1)

    def test_error_fails(self):
        self._case("Ran 1 test\nERROR\n", 1)


class TestGateRunsFromAnyCwd(unittest.TestCase):
    def setUp(self):
        self._outside = tempfile.mkdtemp(prefix="gate-cwd-")

    def test_discuss_gate_from_outside_repo(self):
        rc = subprocess.run(
            ["bash", str(DISCUSS_GATE)],
            cwd=self._outside, capture_output=True, text=True,
        ).returncode
        self.assertEqual(rc, 0, "zj-discuss gate must run from any cwd")

    def test_ui_gate_from_outside_repo(self):
        rc = subprocess.run(
            ["bash", str(UI_GATE)],
            cwd=self._outside, capture_output=True, text=True,
            env={**__import__("os").environ, "PYTHON": sys.executable},
        ).returncode
        self.assertEqual(rc, 0, "ui gate must run from any cwd")


if __name__ == "__main__":
    unittest.main()
