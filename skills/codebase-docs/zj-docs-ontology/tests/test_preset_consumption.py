#!/usr/bin/env python3
"""Ruling 1 / roadmap 1-1-3: docs_governance.py consumes canonical-preset.json.

Regression guards for the preset-consumption seam only:
  - no hardcoded LONG_LIVED / PROCESS constants survive;
  - categories are derived from the shipped preset (skill-root sibling);
  - a missing preset emits PRESET_UNAVAILABLE (signal, exit 0) and makes no
    long-lived/process claims — never a hardcoded fallback;
  - the report exposes the preset it used.

Diagnostic codes whose evidence needs page front matter or a git HEAD roster
(PRESET_VOCABULARY_VIOLATION / PRESET_DIVERGENCE / BASELINE_NOT_APPLICABLE /
UNDECLARED_RETIREMENT) are out of this node's scope — they are pinned by the
P1a red-test and per-code assertion nodes.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("docs_governance", SKILL_ROOT / "scripts" / "docs_governance.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

CASE = Path("tmp/skills-outputs/zj-docs-ontology/_preset_consumption_case")


def write_case_fixture() -> None:
    """Build the shared governance target fixture.

    Both PresetConsumptionTest and ExitCodeTest run the real tool against this
    directory. The fixture is owned per-test (created in setUp, removed in
    tearDown) so neither class can depend on another's setup/teardown ordering.
    """
    if CASE.exists():
        shutil.rmtree(CASE)
    (CASE / "docs" / "ontology").mkdir(parents=True)
    (CASE / "docs" / "ontology" / "ONTOLOGY.md").write_text("# Ontology\n", encoding="utf-8")
    (CASE / "docs" / "plans").mkdir(parents=True)
    (CASE / "docs" / "plans" / "active.md").write_text("# Plan\n", encoding="utf-8")
    (CASE / "docs" / "adversarial").mkdir(parents=True)


def remove_case_fixture() -> None:
    if CASE.exists():
        shutil.rmtree(CASE)


class HardcodedVocabularyTest(unittest.TestCase):
    """P0 fixture (e) preset-single-source: no second copy in the script."""

    def test_no_long_lived_or_process_constant(self) -> None:
        self.assertFalse(hasattr(TOOL, "LONG_LIVED"), "LONG_LIVED constant must be deleted")
        self.assertFalse(hasattr(TOOL, "PROCESS"), "PROCESS constant must be deleted")

    def test_source_has_no_hardcoded_category_tuple(self) -> None:
        source = (SKILL_ROOT / "scripts" / "docs_governance.py").read_text(encoding="utf-8")
        self.assertNotIn("LONG_LIVED =", source)
        self.assertNotIn("PROCESS =", source)


class PresetLoadingTest(unittest.TestCase):
    def test_default_preset_is_a_skill_root_sibling(self) -> None:
        preset = TOOL.load_preset()
        self.assertIsInstance(preset, dict)
        self.assertEqual("normative", preset["status"])
        cats = preset["categories"]
        self.assertIn("ontology", cats["long_lived"])
        self.assertIn("plans", cats["process"])
        self.assertIn("zj-retros", cats["process"])

    def test_categories_are_derived_from_preset_not_hardcoded(self) -> None:
        long_lived, process = TOOL.preset_categories(TOOL.load_preset())
        self.assertIn("ontology", long_lived)
        self.assertNotIn("ontology", process)
        self.assertIn("plans", process)

    def test_missing_preset_returns_none_with_signal(self) -> None:
        self.assertIsNone(TOOL.load_preset(CASE / "no-such-preset.json"))
        self.assertEqual(
            "PRESET_UNAVAILABLE",
            TOOL.preset_unavailable_diagnostic(CASE / "no-such-preset.json")["code"],
        )


class PresetConsumptionTest(unittest.TestCase):
    def setUp(self) -> None:
        write_case_fixture()

    def tearDown(self) -> None:
        remove_case_fixture()

    def test_inventory_categories_follow_the_preset(self) -> None:
        payload = TOOL.report(CASE, validate_links=False)
        inv = payload["inventory"]
        self.assertIn("ontology", inv["long_lived"])
        self.assertIn("docs/ontology/ONTOLOGY.md", inv["long_lived"]["ontology"])
        self.assertIn("plans", inv["process_material"])
        self.assertIn("docs/plans/active.md", inv["process_material"]["plans"])
        self.assertNotIn("ontology", inv["process_material"])
        # A directory outside the preset is reported as target-defined, never
        # silently adopted as a preset category.
        self.assertIn("adversarial", inv["target_defined_categories"])

    def test_report_exposes_the_preset_it_used(self) -> None:
        payload = TOOL.report(CASE, validate_links=False)
        meta = payload["canonical_preset"]
        self.assertTrue(meta["available"])
        self.assertEqual("canonical-preset/v1", meta["schema_version"])

    def test_missing_preset_is_a_signal_with_no_category_claims(self) -> None:
        payload = TOOL.report(CASE, validate_links=False, preset_path=CASE / "missing.json")
        self.assertIn("PRESET_UNAVAILABLE", {d["code"] for d in payload["diagnostics"]})
        self.assertEqual({}, payload["inventory"]["long_lived"])
        self.assertEqual({}, payload["inventory"]["process_material"])
        self.assertFalse(TOOL.has_error(payload))
        self.assertFalse(payload["canonical_preset"]["available"])


class ExitCodeTest(unittest.TestCase):
    def setUp(self) -> None:
        write_case_fixture()

    def tearDown(self) -> None:
        remove_case_fixture()

    def exit_code(self, *args: str) -> int:
        import subprocess

        return subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "docs_governance.py"), *args],
            capture_output=True,
            text=True,
        ).returncode

    def test_default_cli_still_exits_zero(self) -> None:
        self.assertEqual(0, self.exit_code(str(CASE), "--validate"))

    def test_missing_preset_cli_exits_zero(self) -> None:
        self.assertEqual(0, self.exit_code(str(CASE), "--validate", "--preset", str(CASE / "missing.json")))


if __name__ == "__main__":
    unittest.main()
