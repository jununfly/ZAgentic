#!/usr/bin/env python3
"""Regression tests for the opt-in documentation health meter."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("doc_health", SKILL_ROOT / "scripts" / "doc_health.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SPEC.loader.exec_module(TOOL) or TOOL


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TempRepoTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def config(self, payload: dict) -> Path:
        return write(self.root / "docs" / "doc-health.json", json.dumps(payload))

    def outliers(self) -> list[dict[str, str]]:
        return TOOL.measure(self.root, json.loads((self.root / "docs" / "doc-health.json").read_text()))

    def codes(self) -> list[str]:
        return [o["code"] for o in self.outliers()]


class OptInBoundaryTest(TempRepoTest):
    def test_no_config_measures_nothing(self) -> None:
        write(self.root / "docs" / "prds" / "huge.md", "# x\n" * 500)
        config_path, config = TOOL.load_config(self.root, None)
        self.assertIsNone(config_path)
        self.assertIsNone(config)

    def test_malformed_config_is_config_error_not_clean(self) -> None:
        write(self.root / "docs" / "doc-health.json", "{not json")
        path, config = TOOL.load_config(self.root, None)
        self.assertIsNotNone(path)
        self.assertIsInstance(config, str)


class BudgetTest(TempRepoTest):
    def test_over_cap_is_reported_with_the_rule(self) -> None:
        write(self.root / "docs" / "prds" / "big.md", "# x\n" * 30)
        self.config({"budgets": [{"glob": "docs/prds/*.md", "max_lines": 10}]})
        self.assertEqual(["BUDGET_EXCEEDED"], self.codes())

    def test_under_cap_is_clean(self) -> None:
        write(self.root / "docs" / "prds" / "small.md", "# x\n" * 5)
        self.config({"budgets": [{"glob": "docs/prds/*.md", "max_lines": 10}]})
        self.assertEqual([], self.codes())

    def test_the_glob_scopes_the_budget(self) -> None:
        write(self.root / "docs" / "designs" / "big.md", "# x\n" * 30)
        self.config({"budgets": [{"glob": "docs/prds/*.md", "max_lines": 10}]})
        self.assertEqual([], self.codes())


class FreshnessTest(TempRepoTest):
    def page_and_source(self) -> None:
        write(self.root / "docs" / "prds" / "billing.md", "---\ntitle: billing\n---\n\n# Billing\n\n## Source map\n\n- [engine](../../src/billing/engine.rs)\n")
        write(self.root / "src" / "billing" / "engine.rs", "fn main() {}\n")
        old = time.time() - 90 * 86400
        os.utime(self.root / "docs" / "prds" / "billing.md", (old, old))

    def test_source_newer_than_page_drifts(self) -> None:
        self.page_and_source()
        self.config({"freshness": {"max_age_days": 30}})
        self.assertEqual(["FRESHNESS_DRIFT"], self.codes())

    def test_fresh_page_is_clean(self) -> None:
        self.page_and_source()
        self.config({"freshness": {"max_age_days": 400}})
        self.assertEqual([], self.codes())

    def test_a_page_without_a_source_map_is_skipped(self) -> None:
        write(self.root / "docs" / "prds" / "plain.md", "# no source map here\n")
        os.utime(self.root / "docs" / "prds" / "plain.md", (time.time() - 900 * 86400,) * 2)
        self.config({"freshness": {"max_age_days": 30}})
        self.assertEqual([], self.codes())


class OrphanTest(TempRepoTest):
    def graph(self) -> None:
        write(self.root / "docs" / "README.md", "# map\n\n- [a](prds/a.md)\n")
        write(self.root / "docs" / "prds" / "a.md", "# A\n\nSee [b](b.md).\n")
        write(self.root / "docs" / "prds" / "b.md", "# B\n")
        write(self.root / "docs" / "prds" / "orphan.md", "# nobody knows me\n")

    def test_zero_indegree_is_reported(self) -> None:
        self.graph()
        self.config({"orphans": True})
        self.assertIn("ZERO_INDEGREE", self.codes())
        entry = next(o for o in self.outliers() if o["code"] == "ZERO_INDEGREE")
        self.assertEqual("docs/prds/a.md", entry["path"])

    def test_orphan_is_reported(self) -> None:
        self.graph()
        self.config({"orphans": True})
        entry = next(o for o in self.outliers() if o["code"] == "ORPHAN_PAGE")
        self.assertEqual("docs/prds/orphan.md", entry["path"])

    def test_cited_pages_are_not_reported(self) -> None:
        self.graph()
        self.config({"orphans": True})
        self.assertNotIn("docs/prds/b.md", [o["path"] for o in self.outliers()])

    def test_evidence_surfaces_are_not_link_sources(self) -> None:
        self.graph()
        write(self.root / "skills-outputs" / "sweep" / "note.md", "cites [a](../../docs/prds/a.md)\n")
        self.config({"orphans": True})
        self.assertIn("ZERO_INDEGREE", self.codes())


class OnlyReadsTest(TempRepoTest):
    def test_the_tool_never_writes(self) -> None:
        write(self.root / "docs" / "prds" / "big.md", "# x\n" * 30)
        write(self.root / "docs" / "README.md", "# map\n\n- [big](prds/big.md)\n")
        self.config({"budgets": [{"glob": "docs/**/*.md", "max_lines": 10}], "orphans": True})
        before = sorted((p, p.stat().st_mtime_ns, p.read_bytes()) for p in self.root.rglob("*") if p.is_file())
        TOOL.measure(self.root, json.loads((self.root / "docs" / "doc-health.json").read_text()))
        after = sorted((p, p.stat().st_mtime_ns, p.read_bytes()) for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(before, after)


class CommandLineTest(unittest.TestCase):
    def run_cli(self, root: Path) -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "doc_health.py"), str(root)],
            capture_output=True, text=True,
        )
        return result.returncode, json.loads(result.stdout)

    def test_unconfigured_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, payload = self.run_cli(Path(tmp))
            self.assertEqual(0, code)
            self.assertEqual("opt-in", payload["status"])

    def test_outliers_exit_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "docs" / "prds" / "big.md", "# x\n" * 30)
            write(root / "docs" / "doc-health.json", json.dumps({"budgets": [{"glob": "docs/prds/*.md", "max_lines": 10}]}))
            code, payload = self.run_cli(root)
            self.assertEqual(1, code)
            self.assertEqual("measured", payload["status"])
            self.assertEqual("BUDGET_EXCEEDED", payload["outliers"][0]["code"])

    def test_clean_configured_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "docs" / "prds" / "small.md", "# x\n" * 3)
            write(root / "docs" / "doc-health.json", json.dumps({"budgets": [{"glob": "docs/prds/*.md", "max_lines": 10}]}))
            code, payload = self.run_cli(root)
            self.assertEqual(0, code)
            self.assertEqual([], payload["outliers"])

    def test_config_error_exit_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "docs" / "doc-health.json", "{oops")
            code, payload = self.run_cli(root)
            self.assertEqual(1, code)
            self.assertEqual("config-error", payload["status"])


if __name__ == "__main__":
    unittest.main()
