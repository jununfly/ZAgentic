#!/usr/bin/env python3
"""Regression guard: the two FACT_NO_SINGLE_HOME signals are adjudicated
legitimate exceptions, not defects waiting to be 'fixed'.

The seam is the repository root test suite. These tests treat the map, the two
pages, and the governance tool's output as public artifacts — they do not emit
new runtime diagnostics, so FACT_NO_SINGLE_HOME stays a signal rather than
becoming a gate.

Why this guard exists (decay barrier): a prose exception entry in the doc map
is passive — three months later nobody remembers it, and the next reader either
'repairs' the heading (breaking the vocabulary-SSOT / route-table separation) or
starts ignoring all signals (letting a real duplicate slip through). This guard
converts that soft convention into a hard assertion: any drift in the signal
set, the justification, or the underlying bounded-question content turns red
and forces a fresh adjudication.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOVERNANCE = (
    REPO / "skills" / "codebase-docs" / "zj-docs-ontology" / "scripts"
    / "docs_governance.py"
)
MAP = REPO / "docs" / "README.md"
ZJ_CONTEXT = REPO / "ZJ-CONTEXT.md"
ZJ_GUIDE = REPO / "skills" / "engineering" / "zj-guide" / "SKILL.md"

# The adjudicated set is an independent specification literal from the
# 2026-11-20 governance pass, NOT recomputed from the tool output. A new
# exception must be added here deliberately — that friction is the point.
KNOWN_EXCEPTION_HEADINGS = {"codebase documentation", "ui delivery"}
TOPIC = "docs-reorg-2026-11"

# Heading extracted from the tool's FACT_NO_SINGLE_HOME message. Mirrors the
# tool's own normalize_heading (lowercase + non-word -> space) only insofar as
# the message already carries the normalized form in single quotes.
FACT_RE = re.compile(r"no single home for fact '([^']+)':")


def fact_signal_headings() -> set[str]:
    """Run the real governance validator and collect FACT_NO_SINGLE_HOME ids."""
    result = subprocess.run(
        [sys.executable, str(GOVERNANCE), str(REPO),
         "--validate", "--topic", TOPIC],
        capture_output=True, text=True, cwd=REPO,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"governance validator crashed (rc={result.returncode}): {result.stderr[-500:]}"
        )
    report = json.loads(result.stdout)
    found: set[str] = set()
    for diag in report.get("diagnostics", []):
        if diag.get("code") != "FACT_NO_SINGLE_HOME":
            continue
        match = FACT_RE.search(diag.get("message", ""))
        if match:
            found.add(match.group(1))
    return found


def map_exception_body() -> str:
    """Body of the doc-map audit-exception section."""
    lines = MAP.read_text(encoding="utf-8").splitlines()
    body: list[str] = []
    found = False
    for line in lines:
        if line.startswith("## "):
            if found:
                break
            found = line.strip() == "## 审计例外（doc-slop）"
            continue
        if found:
            body.append(line)
    return "\n".join(body)


class FactHomeExceptionSetTest(unittest.TestCase):
    """The signal set is exactly the adjudicated exceptions — no more, no less."""

    def test_signal_set_matches_adjudicated_exceptions(self) -> None:
        actual = fact_signal_headings()
        self.assertEqual(
            actual, KNOWN_EXCEPTION_HEADINGS,
            "FACT_NO_SINGLE_HOME drifted. A new duplicate heading needs a fresh "
            "adjudication (add to the map exception table AND this constant with "
            "a reason); a missing one means someone 'fixed' a legitimate "
            "vocabulary-SSOT / route-table split.",
        )


class ExceptionJustificationTest(unittest.TestCase):
    """The rationale is a durable artifact: it cannot be quietly edited away."""

    def test_headings_and_reasons_registered_in_map(self) -> None:
        body = map_exception_body()
        self.assertNotEqual("", body.strip(), "doc map must declare audit exceptions")
        for anchor in ("codebase documentation", "ui delivery", "duplicate-heading"):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, body)
        for reason in ("bounded question 不同", "coarse filter", "remedy 是选 home"):
            with self.subTest(reason=reason):
                self.assertIn(reason, body)


class BoundedQuestionContentTest(unittest.TestCase):
    """Both pages keep the content that justifies the split — killing the signal
    by deleting content must turn red."""

    def test_zj_context_keeps_vocabulary_definitions(self) -> None:
        text = ZJ_CONTEXT.read_text(encoding="utf-8")
        for term in ("Codebase docs", "Document map", "Long-lived document",
                     "UI delivery chain", "Experience Version"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_zj_guide_keeps_route_table(self) -> None:
        text = ZJ_GUIDE.read_text(encoding="utf-8")
        for anchor in (
            "Use this route when the job is to establish, migrate, navigate, or govern",
            "`/zj-docs-ontology`",
            "A single chain from a sentence to a handed-off interface",
            "`/zj-ui-brief`",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
