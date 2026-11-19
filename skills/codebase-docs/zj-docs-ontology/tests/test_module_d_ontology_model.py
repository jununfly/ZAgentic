#!/usr/bin/env python3
"""Module D: ontology model validation against the meta-schema.

Bidirectional per repo discipline: each defect variant must produce its named
ERROR (red before implementation), the valid model must be fully green
(zero diagnostics, full coverage), and the coverage invariant must stay a
signal — a missing receipt never blocks with an ERROR.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "ontology-model"
SPEC = importlib.util.spec_from_file_location(
    "validate_ontology_model", SKILL_ROOT / "scripts" / "validate_ontology_model.py"
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def run_cli(repo: Path, model: Path) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "validate_ontology_model.py"),
         str(repo), "--model", str(model)],
        capture_output=True, text=True,
    )
    import json
    return json.loads(proc.stdout), proc.returncode


def codes(report: dict) -> set[str]:
    return {d["code"] for d in report["diagnostics"]}


class ValidModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.report, self.exit_code = run_cli(FIXTURE, FIXTURE / "model.json")

    def test_valid_model_has_zero_diagnostics(self) -> None:
        self.assertEqual(self.report["diagnostics"], [])

    def test_valid_model_exits_zero(self) -> None:
        self.assertEqual(self.exit_code, 0)

    def test_coverage_is_full(self) -> None:
        self.assertEqual(self.report["coverage"]["uncovered"], 0)
        self.assertEqual(self.report["coverage"]["receipts"], 3)


class StructuralErrorVariantsTest(unittest.TestCase):
    def run_variant(self, name: str) -> tuple[dict, int]:
        return run_cli(FIXTURE, FIXTURE / "variants" / f"{name}.json")

    def test_duplicate_id_is_an_error(self) -> None:
        report, code = self.run_variant("duplicate-id")
        self.assertIn("ONTOLOGY_ID_DUPLICATE", codes(report))
        self.assertEqual(code, 1)

    def test_orphan_attribute_is_an_error(self) -> None:
        report, code = self.run_variant("orphan-attribute")
        self.assertIn("ONTOLOGY_ATTRIBUTE_ORPHAN", codes(report))
        self.assertEqual(code, 1)

    def test_missing_relation_endpoint_is_an_error(self) -> None:
        report, code = self.run_variant("missing-endpoint")
        self.assertIn("ONTOLOGY_RELATION_ENDPOINT_MISSING", codes(report))
        self.assertEqual(code, 1)

    def test_bad_rule_trace_is_an_error(self) -> None:
        report, code = self.run_variant("bad-trace")
        self.assertIn("ONTOLOGY_RULE_TRACE_MISSING", codes(report))
        self.assertEqual(code, 1)

    def test_broken_receipt_is_an_error(self) -> None:
        report, code = self.run_variant("broken-receipt")
        self.assertIn("ONTOLOGY_PAGE_RECEIPT_BROKEN", codes(report))
        self.assertEqual(code, 1)

    def test_missing_required_field_is_an_error(self) -> None:
        report, code = self.run_variant("missing-required")
        self.assertIn("ONTOLOGY_REQUIRED_FIELD_MISSING", codes(report))
        self.assertEqual(code, 1)

    def test_unknown_schema_version_is_an_error(self) -> None:
        report, code = self.run_variant("unknown-schema")
        self.assertIn("ONTOLOGY_MODEL_SCHEMA_UNSUPPORTED", codes(report))
        self.assertEqual(code, 1)


class CoverageInvariantTest(unittest.TestCase):
    def test_uncovered_page_is_a_signal_not_an_error(self) -> None:
        report, code = run_cli(FIXTURE, FIXTURE / "variants" / "uncovered.json")
        self.assertIn("CONTENT_UNCOVERED", codes(report))
        self.assertNotIn("ONTOLOGY_PAGE_RECEIPT_BROKEN", codes(report))
        self.assertEqual(code, 0)
        self.assertEqual(report["coverage"]["uncovered"], 1)
        self.assertEqual(report["coverage"]["uncovered_pages"], ["docs/designs/rules.md"])

    def test_content_uncovered_is_registered_as_a_signal(self) -> None:
        self.assertNotIn("CONTENT_UNCOVERED", TOOL.ERROR_CODES)
        self.assertIn("CONTENT_UNCOVERED", TOOL.SIGNAL_CODES)


class MetaSchemaSingleSourceTest(unittest.TestCase):
    def test_meta_schema_declares_the_exit_semantics(self) -> None:
        import json
        meta = json.loads(
            (SKILL_ROOT / "references" / "ontology-meta-schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            frozenset(meta["exit_semantics"]["error_codes"]), TOOL.ERROR_CODES
        )
        self.assertEqual(
            frozenset(meta["exit_semantics"]["signal_codes"]), TOOL.SIGNAL_CODES
        )

    def test_required_fields_come_from_meta_schema(self) -> None:
        import json
        meta = json.loads(
            (SKILL_ROOT / "references" / "ontology-meta-schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(meta["classes"]["rule"]["required"], ["id", "statement", "traces"])
        self.assertEqual(meta["page_receipt"]["required"], ["path", "elements"])


if __name__ == "__main__":
    unittest.main()
