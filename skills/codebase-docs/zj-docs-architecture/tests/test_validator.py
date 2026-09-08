#!/usr/bin/env python3
"""Contract tests for the bounded architecture documentation validator."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
MODULE_PATH = SKILL_ROOT / "scripts" / "validate_architecture_docs.py"
SPEC = importlib.util.spec_from_file_location("architecture_validator", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class ArchitectureValidatorTest(unittest.TestCase):
    def codes(self, fixture: str) -> set[str]:
        diagnostics, _, _ = VALIDATOR.validate(FIXTURES / fixture)
        return {item.code for item in diagnostics}

    def test_accepts_minimal_and_multiview_handbooks(self) -> None:
        self.assertEqual(self.codes("valid-minimal"), set())
        self.assertEqual(self.codes("valid-multiview"), set())

    def test_accepts_a_lazy_architecture_category(self) -> None:
        self.assertEqual(self.codes("valid-lazy"), set())

    def test_rejects_duplicate_authority_and_source_drift(self) -> None:
        self.assertIn("AUTHORITY_ID_DUPLICATE", self.codes("invalid-duplicate-authority"))
        self.assertIn("SOURCE_TARGET_MISSING", self.codes("invalid-source-drift"))

    def test_rejects_unaccepted_adr(self) -> None:
        self.assertIn("ADR_UNACCEPTED", self.codes("invalid-adr"))

    def test_never_reads_process_or_fixture_payloads(self) -> None:
        diagnostics, reads, _ = VALIDATOR.validate(FIXTURES / "read-boundary")
        self.assertEqual(diagnostics, [])
        self.assertFalse(any(path.endswith("docs/plans/active.md") for path in reads))
        self.assertFalse(any(path.endswith("fixtures/payload.json") for path in reads))


if __name__ == "__main__":
    unittest.main()
