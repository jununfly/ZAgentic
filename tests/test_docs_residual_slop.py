#!/usr/bin/env python3
"""Regression guards for the M7 residual-slop disposition.

Seam (confirmed with the Human): the repository root test suite. These tests
observe documentation pages as public artifacts. They do not emit runtime
diagnostics, so the doc-slop checklist remains an audit list rather than a gate
(see zj-docs-ontology's ``test_it_stays_an_audit_list_not_a_gate``).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
MAP = DOCS / "README.md"
DESIGN = DOCS / "designs" / "zj-discuss" / "design.md"
ADR0010 = DOCS / "zj-adr" / "0010-local-file-persistence-convention.md"
PRD = DOCS / "prds" / "codebase-docs-capability.md"
AGREEMENT = DOCS / "agreements" / "product-project-graphical-cross-comparison-model.md"
ADR0005 = DOCS / "zj-adr" / "0005-composer-authority-and-plan-contract.md"
COMPOSER_DESIGN = DOCS / "designs" / "zj-composer-plan-product-form.md"
DESIGN_LINK = "../designs/zj-composer-plan-product-form.md"

# Independent specification value, not a recomputed snapshot: the 2026-11-08
# baseline was 687 shared 10-grams, and a historical ADR should not restate a
# third of the primary design page. Restating it again must turn this red.
OVERLAP_CEILING = 450

EXEMPTION_HEADING = "## 审计例外（doc-slop）"
EXEMPTION_ANCHORS = (
    "agreement 的规范性模态句",
    "ADR 历史台账",
    "PRD 验收清单",
)
EXEMPTION_REASONS = ("规范性契约", "史据", "验收标准")


def section(text: str, heading: str) -> str:
    """Body of one ``## `` section, or an empty string when it is absent."""
    current: list[str] = []
    found = False
    for line in text.splitlines():
        if line.startswith("## "):
            if found:
                return "\n".join(current)
            found = line.strip() == heading
            current = []
        elif found:
            current.append(line)
    return "\n".join(current) if found else ""


class ExemptionRegistrationTest(unittest.TestCase):
    """Contract text cannot be quietly edited away: each legit exception to the
    slop checklist has to be named in the doc map together with its reason."""

    def test_slop_exemptions_are_registered_with_reasons(self) -> None:
        body = section(MAP.read_text(encoding="utf-8"), EXEMPTION_HEADING)
        self.assertNotEqual("", body.strip(), "doc map must declare the audit exceptions")
        for anchor in EXEMPTION_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, body)
        for reason in EXEMPTION_REASONS:
            with self.subTest(reason=reason):
                self.assertIn(reason, body)


LEDGER_MARKER = "历史台账"
LEDGER_ROWS = ("| R1 |", "| R2 |", "| R3 |", "| R4 |", "| R5 |", "| R6 |", "| R7 |")
CONTRACT_ANCHORS = (
    "不得用于排序、裁决、回灌或确定优先级",
    "差异条目清单是唯一结论载体",
)


class HistoricalLedgerTest(unittest.TestCase):
    """A ledger is evidence, not progress. Declaring it, and keeping the
    primary SSOT's normative sentences, are both observable behaviours."""

    def test_historical_ledger_is_declared_and_anchors_survive(self) -> None:
        design = DESIGN.read_text(encoding="utf-8")
        self.assertTrue(
            LEDGER_MARKER in design,
            "the status ledger must be declared, not silently edited",
        )
        for row in LEDGER_ROWS:
            with self.subTest(row=row):
                self.assertIn(row, design)
        self.assertIn("已 RATIFIED", design)
        self.assertLess(
            design.index(LEDGER_MARKER), design.index("| R1 |"),
            "the declaration must come before the ledger rows",
        )

        # Independent known literals from the 2026-11-08 inventory: a lower
        # bound, not a recomputed snapshot, so removing evidence turns red.
        self.assertGreaterEqual(ADR0010.read_text(encoding="utf-8").count("✅"), 13)
        self.assertGreaterEqual(
            len(re.findall(r"-\s*\[ \]", PRD.read_text(encoding="utf-8"))), 9
        )
        agreement = AGREEMENT.read_text(encoding="utf-8")
        for anchor in CONTRACT_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, agreement)


def ten_grams(text: str, n: int = 10) -> set[str]:
    """Whitespace/punctuation-insensitive character n-grams of a document."""
    flat = re.sub(r"[\s`*|#\[\]()（）「」、，。；：/·→<>=+_\-—!？?\.,:]", "", text)
    return {flat[i : i + n] for i in range(max(0, len(flat) - n + 1))}


class RationaleHomeTest(unittest.TestCase):
    """A historical ADR owns the verdict; the primary design page owns the
    full rationale. Restating the rationale in both places is the defect."""

    def test_adr0005_defers_rationale_to_the_design_page(self) -> None:
        adr = ADR0005.read_text(encoding="utf-8")
        design = COMPOSER_DESIGN.read_text(encoding="utf-8")
        overlap = len(ten_grams(adr) & ten_grams(design))
        self.assertLessEqual(
            overlap, OVERLAP_CEILING,
            f"ADR restates the design page's rationale: {overlap} shared 10-grams",
        )
        decision = section(adr, "## Decision")
        self.assertNotEqual("", decision.strip())
        self.assertIn(DESIGN_LINK, decision, "the Decision must point at the primary home")
        for heading in ("## Consequences", "## Evidence"):
            with self.subTest(heading=heading):
                self.assertIn(heading, adr)
        self.assertIn(DESIGN_LINK, adr)
        self.assertTrue(COMPOSER_DESIGN.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
