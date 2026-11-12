"""Governance guards for the roadmap visual-review slice (2026-11-12 review).

These observe published artifacts only: CLI reference, terminology glossary,
spec/product pages, and the required CI workflow. No internal function imported.
"""
from __future__ import annotations

import json
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "codebase-docs" / "zj-roadmap-driven"
CLI_REF = SKILL / "references" / "roadmap-cli.md"
CONTEXT = REPO / "ZJ-CONTEXT.md"
PRODUCT = REPO / "docs" / "designs" / "zj-roadmap-visual-review-product.md"
SPEC = REPO / "docs" / "designs" / "zj-roadmap-visual-review.spec.json"
TECH = REPO / "docs" / "designs" / "zj-roadmap-visual-review-technical.md"
WORKFLOW = REPO / ".github" / "workflows" / "skill-closure-lint.yml"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


class PublishedEntryPoints(unittest.TestCase):
    def test_cli_reference_registers_the_readonly_visualization_entry(self):
        body = _read(CLI_REF)
        self.assertIn("只读可视化", body)
        self.assertIn("viz.cli", body)
        self.assertIn("--out", body)

    def test_no_implicit_cwd_output_in_cli_source(self):
        self.assertNotIn(
            'Path(args.roadmap).stem + ".viz.html"',
            _read(SKILL / "viz" / "cli.py"),
            "implicit cwd default came back (ADR 0010)",
        )


class GlossaryContract(unittest.TestCase):
    TERMS = (
        "DOI", "theta calibration", "LOD", "zj-roadmap-anchor/v1",
        "dependency projection", "context side-pack", "mandatory-set",
        "budget overflow",
    )

    def test_new_domain_terms_are_registered_before_merge(self):
        body = _read(CONTEXT)
        missing = [term for term in self.TERMS if term not in body]
        self.assertEqual([], missing, f"AGENTS.md:41 unregistered terms: {missing}")


class DeliveredScopeContract(unittest.TestCase):
    def test_product_page_records_the_amended_delivery_boundary(self):
        body = _read(PRODUCT)
        self.assertIn("## Amendment (2026-11-12)", body)
        self.assertIn("S1 delivered", body)
        self.assertIn("S1", body)

    def test_viz_package_no_longer_claims_s1_is_future_work(self):
        self.assertNotIn("按路线图后续切片落地",
                         _read(SKILL / "viz" / "__init__.py"))

    def test_cli_reference_registers_s1_entrypoints(self):
        body = _read(CLI_REF)
        for flag in ("--ir", "--receipt", "--delta"):
            self.assertIn(flag, body, f"S1 flag {flag} is not published")

    def test_s1_exit_criteria_were_not_silently_dropped(self):
        spec = json.loads(_read(SPEC))
        slices = {s["id"]: s for s in spec["slices"]}
        self.assertIn("S1", slices)
        self.assertIn("两 carrier 同 anchor 输出逐字节相同", slices["S1"]["exit-criteria"])

    def test_technical_page_no_longer_claims_no_runtime_was_delivered(self):
        self.assertNotIn("本次交付只落规格与机械闸门，不改 skill 运行时实现。", _read(TECH))


class RequiredCoverageContract(unittest.TestCase):
    def test_required_job_actually_runs_the_new_guards(self):
        body = _read(WORKFLOW)
        for needle in (
            "validate-skill-frontmatter.py",
            "roadmap_visual_review_spec.py verify",
            "test_roadmap_visual_review_spec",
            "viz.tests.test_viz",
            "pip install -r requirements.txt",
        ):
            self.assertIn(needle, body, f"required job does not run {needle!r}")

    def test_required_job_stays_unfiltered(self):
        body = _read(WORKFLOW)
        head = body.split("jobs:")[0]
        self.assertNotIn("paths:", head, "a filtered required check blocks unrelated PRs (#211)")


class SyncTransportVerdict(unittest.TestCase):
    """The open item is closed by a decision, not by building a daemon."""

    def test_automatic_receipt_sync_is_an_explicit_rejected_default(self):
        rejected = {
            item["id"]: item
            for item in json.loads(_read(SPEC))["rejected-defaults"]
        }
        self.assertIn("RD::14", rejected)
        item = rejected["RD::14"]
        text = item["statement"] + item["reason"]
        for word in ("后台", "自动同步", "网络"):
            self.assertIn(word, text)
        for word in ("可丢弃", "显式", "fail-closed"):
            self.assertIn(word, item["reason"])

    def test_product_ledger_records_a_decision_not_an_open_item(self):
        body = _read(PRODUCT)
        self.assertIn("已判决", body)
        self.assertIn("RD::14", body)
        self.assertNotIn("仍 open（范围外，非缺陷）", body)

    def test_cli_reference_publishes_repeatable_peer_import(self):
        body = _read(CLI_REF)
        self.assertIn("可重复", body)
        self.assertIn("--merge-receipt", body)

    def test_required_job_runs_the_governance_guard(self):
        self.assertIn("tests.test_roadmap_visual_review_governance",
                      _read(WORKFLOW))


if __name__ == "__main__":
    unittest.main()
